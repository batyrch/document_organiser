/**
 * IPC Handlers - Register handlers for renderer-to-main communication.
 *
 * These handlers forward requests to the Python bridge and return results
 * to the renderer process.
 */

import { ipcMain, IpcMainInvokeEvent } from 'electron';
import { getPythonBridge } from './python-bridge';
import {
  IPC_CHANNELS,
  FilesListParams,
  FilesListResult,
  FilesAnalyzeParams,
  FilesAnalyzeResult,
  FilesMoveParams,
  FilesMoveResult,
  FilesDeleteParams,
  FilesDeleteResult,
  SettingsGetResult,
  SettingsSetParams,
  SettingsSetResult,
  JDGetAreasResult,
  PythonStatusEvent,
} from '../shared/types';

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Create an IPC handler that forwards to the Python bridge.
 */
function createPythonHandler<TParams, TResult>(
  channel: string,
  method: string
): void {
  ipcMain.handle(
    channel,
    async (_event: IpcMainInvokeEvent, params: TParams): Promise<TResult> => {
      const bridge = getPythonBridge();
      return bridge.send<TResult>(method, params as Record<string, unknown>);
    }
  );
}

// =============================================================================
// Register Handlers
// =============================================================================

/**
 * Register all IPC handlers.
 * Call this during app initialization.
 */
export function registerIPCHandlers(): void {
  console.log('[IPC] Registering handlers...');

  // File operations
  createPythonHandler<FilesListParams, FilesListResult>(
    IPC_CHANNELS.FILES_LIST,
    'files:list'
  );

  createPythonHandler<FilesAnalyzeParams, FilesAnalyzeResult>(
    IPC_CHANNELS.FILES_ANALYZE,
    'files:analyze'
  );

  createPythonHandler<FilesMoveParams, FilesMoveResult>(
    IPC_CHANNELS.FILES_MOVE,
    'files:move'
  );

  createPythonHandler<FilesDeleteParams, FilesDeleteResult>(
    IPC_CHANNELS.FILES_DELETE,
    'files:delete'
  );

  // Settings
  createPythonHandler<Record<string, never>, SettingsGetResult>(
    IPC_CHANNELS.SETTINGS_GET,
    'settings:get'
  );

  createPythonHandler<SettingsSetParams, SettingsSetResult>(
    IPC_CHANNELS.SETTINGS_SET,
    'settings:set'
  );

  // JD System
  createPythonHandler<Record<string, never>, JDGetAreasResult>(
    IPC_CHANNELS.JD_GET_AREAS,
    'jd:getAreas'
  );

  // Python bridge status
  ipcMain.handle(
    IPC_CHANNELS.PYTHON_STATUS,
    (): PythonStatusEvent => {
      const bridge = getPythonBridge();
      return {
        status: bridge.ready ? 'ready' : 'starting',
      };
    }
  );

  // Python bridge restart
  ipcMain.handle(IPC_CHANNELS.PYTHON_RESTART, async (): Promise<void> => {
    const bridge = getPythonBridge();
    await bridge.restart();
  });

  console.log('[IPC] Handlers registered');
}

/**
 * Remove all IPC handlers.
 * Call this during app shutdown.
 */
export function removeIPCHandlers(): void {
  console.log('[IPC] Removing handlers...');

  Object.values(IPC_CHANNELS).forEach((channel) => {
    ipcMain.removeHandler(channel);
  });

  console.log('[IPC] Handlers removed');
}
