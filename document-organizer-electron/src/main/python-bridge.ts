/**
 * Python Bridge - Manages communication with the Python backend.
 *
 * Spawns the Python API server as a child process and communicates
 * via JSON over stdin/stdout.
 */

import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import * as path from 'path';
import * as readline from 'readline';
import { v4 as uuidv4 } from 'uuid';
import { app } from 'electron';
import {
  IPCRequest,
  IPCResponse,
  PythonBridgeError,
  PythonStatusEvent,
} from '../shared/types';

// =============================================================================
// Types
// =============================================================================

interface PendingRequest {
  resolve: (value: unknown) => void;
  reject: (error: Error) => void;
  timeout: NodeJS.Timeout;
  method: string;
}

type PythonBridgeEvents = {
  status: [PythonStatusEvent];
  error: [Error];
  stdout: [string];
  stderr: [string];
};

// =============================================================================
// PythonBridge Class
// =============================================================================

export class PythonBridge extends EventEmitter<PythonBridgeEvents> {
  private process: ChildProcess | null = null;
  private pendingRequests: Map<string, PendingRequest> = new Map();
  private isReady = false;
  private isShuttingDown = false;
  private restartAttempts = 0;
  private maxRestartAttempts = 3;
  private restartDelay = 1000;
  private defaultTimeout = 60000; // 60 seconds for AI operations
  private lineReader: readline.Interface | null = null;

  /**
   * Get the path to the Python API server script.
   */
  private getApiServerPath(): string {
    // In development, use the path relative to the project
    // In production, it will be bundled differently
    if (app.isPackaged) {
      // In production, look for bundled Python
      return path.join(process.resourcesPath, 'python', 'api_server.py');
    }

    // In development, use the script in the parent directory
    return path.join(__dirname, '..', '..', '..', 'api_server.py');
  }

  /**
   * Get the Python executable path.
   */
  private getPythonPath(): string {
    // Check for venv first
    const venvPython = path.join(
      __dirname,
      '..',
      '..',
      '..',
      'venv',
      'bin',
      'python'
    );

    // In production, use bundled Python or system Python
    if (app.isPackaged) {
      return 'python3';
    }

    // In development, prefer venv
    return venvPython;
  }

  /**
   * Start the Python process.
   */
  async start(): Promise<void> {
    if (this.process) {
      console.log('[PythonBridge] Process already running');
      return;
    }

    this.isShuttingDown = false;
    this.emit('status', { status: 'starting' });

    const pythonPath = this.getPythonPath();
    const scriptPath = this.getApiServerPath();

    console.log(`[PythonBridge] Starting: ${pythonPath} ${scriptPath}`);

    try {
      this.process = spawn(pythonPath, [scriptPath], {
        stdio: ['pipe', 'pipe', 'pipe'],
        cwd: path.dirname(scriptPath),
        env: {
          ...process.env,
          PYTHONUNBUFFERED: '1', // Disable Python output buffering
        },
      });

      // Set up stdout line reader
      if (this.process.stdout) {
        this.lineReader = readline.createInterface({
          input: this.process.stdout,
          terminal: false,
        });

        this.lineReader.on('line', (line) => {
          this.handleStdoutLine(line);
        });
      }

      // Handle stderr (debug logs)
      if (this.process.stderr) {
        this.process.stderr.on('data', (data) => {
          const message = data.toString();
          console.log(`[Python] ${message.trim()}`);
          this.emit('stderr', message);
        });
      }

      // Handle process errors
      this.process.on('error', (error) => {
        console.error('[PythonBridge] Process error:', error);
        this.emit('error', error);
        this.handleProcessExit(-1);
      });

      // Handle process exit
      this.process.on('exit', (code) => {
        console.log(`[PythonBridge] Process exited with code: ${code}`);
        this.handleProcessExit(code ?? -1);
      });

      // Wait for ready signal
      await this.waitForReady();
    } catch (error) {
      console.error('[PythonBridge] Failed to start:', error);
      this.emit('status', { status: 'error', message: String(error) });
      throw error;
    }
  }

  /**
   * Wait for the Python process to signal readiness.
   */
  private waitForReady(): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Python bridge startup timeout'));
      }, 30000);

      const checkReady = () => {
        if (this.isReady) {
          clearTimeout(timeout);
          resolve();
        } else {
          setTimeout(checkReady, 100);
        }
      };

      checkReady();
    });
  }

  /**
   * Handle a line of output from Python stdout.
   */
  private handleStdoutLine(line: string): void {
    if (!line.trim()) return;

    try {
      const response: IPCResponse = JSON.parse(line);
      this.emit('stdout', line);

      // Handle ready signal
      if (response.id === '__ready__') {
        console.log('[PythonBridge] Python process ready');
        this.isReady = true;
        this.restartAttempts = 0;
        this.emit('status', { status: 'ready' });
        return;
      }

      // Handle error responses
      if (response.id === '__error__') {
        console.error('[PythonBridge] Python error:', response.error);
        return;
      }

      // Find pending request
      const pending = this.pendingRequests.get(response.id);
      if (pending) {
        clearTimeout(pending.timeout);
        this.pendingRequests.delete(response.id);

        if (response.error) {
          pending.reject(
            new PythonBridgeError(response.error, 'PYTHON_ERROR', response)
          );
        } else {
          pending.resolve(response.result);
        }
      } else {
        console.warn(`[PythonBridge] Unknown response ID: ${response.id}`);
      }
    } catch (error) {
      console.error('[PythonBridge] Failed to parse response:', line, error);
    }
  }

  /**
   * Handle Python process exit.
   */
  private handleProcessExit(code: number): void {
    this.isReady = false;
    this.process = null;

    if (this.lineReader) {
      this.lineReader.close();
      this.lineReader = null;
    }

    // Reject all pending requests
    for (const [id, pending] of this.pendingRequests) {
      clearTimeout(pending.timeout);
      pending.reject(new PythonBridgeError('Python process exited', 'PROCESS_EXIT'));
    }
    this.pendingRequests.clear();

    // Attempt restart if not shutting down
    if (!this.isShuttingDown && this.restartAttempts < this.maxRestartAttempts) {
      this.restartAttempts++;
      console.log(
        `[PythonBridge] Restarting (attempt ${this.restartAttempts}/${this.maxRestartAttempts})`
      );
      setTimeout(() => this.start(), this.restartDelay);
    } else if (!this.isShuttingDown) {
      this.emit('status', {
        status: 'error',
        message: 'Max restart attempts reached',
      });
    } else {
      this.emit('status', { status: 'stopped' });
    }
  }

  /**
   * Send a request to the Python process.
   */
  async send<T>(method: string, params: Record<string, unknown> = {}): Promise<T> {
    if (!this.process || !this.isReady) {
      throw new PythonBridgeError(
        'Python bridge not ready',
        'NOT_READY'
      );
    }

    const id = uuidv4();
    const request: IPCRequest = { id, method, params };

    return new Promise<T>((resolve, reject) => {
      // Set up timeout
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(
          new PythonBridgeError(
            `Request timed out: ${method}`,
            'TIMEOUT',
            { method, params }
          )
        );
      }, this.defaultTimeout);

      // Store pending request
      this.pendingRequests.set(id, {
        resolve: resolve as (value: unknown) => void,
        reject,
        timeout,
        method,
      });

      // Send request
      const json = JSON.stringify(request);
      console.log(`[PythonBridge] Sending: ${method}`);

      if (this.process?.stdin) {
        this.process.stdin.write(json + '\n');
      } else {
        clearTimeout(timeout);
        this.pendingRequests.delete(id);
        reject(new PythonBridgeError('Process stdin not available', 'NO_STDIN'));
      }
    });
  }

  /**
   * Stop the Python process.
   */
  async stop(): Promise<void> {
    console.log('[PythonBridge] Stopping...');
    this.isShuttingDown = true;

    if (this.process) {
      // Close stdin to signal shutdown
      if (this.process.stdin) {
        this.process.stdin.end();
      }

      // Wait a bit for graceful shutdown
      await new Promise((resolve) => setTimeout(resolve, 500));

      // Force kill if still running
      if (this.process) {
        this.process.kill();
        this.process = null;
      }
    }

    this.isReady = false;
    this.emit('status', { status: 'stopped' });
  }

  /**
   * Restart the Python process.
   */
  async restart(): Promise<void> {
    await this.stop();
    this.restartAttempts = 0;
    this.isShuttingDown = false;
    await this.start();
  }

  /**
   * Check if the bridge is ready.
   */
  get ready(): boolean {
    return this.isReady;
  }
}

// =============================================================================
// Singleton Instance
// =============================================================================

let bridgeInstance: PythonBridge | null = null;

export function getPythonBridge(): PythonBridge {
  if (!bridgeInstance) {
    bridgeInstance = new PythonBridge();
  }
  return bridgeInstance;
}

export async function initPythonBridge(): Promise<PythonBridge> {
  const bridge = getPythonBridge();
  await bridge.start();
  return bridge;
}

export async function shutdownPythonBridge(): Promise<void> {
  if (bridgeInstance) {
    await bridgeInstance.stop();
    bridgeInstance = null;
  }
}
