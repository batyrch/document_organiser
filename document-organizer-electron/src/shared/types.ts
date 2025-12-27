/**
 * Shared TypeScript types for the Document Organizer Electron app.
 */

// =============================================================================
// File Types
// =============================================================================

export interface FileEntry {
  path: string;
  name: string;
  size: number;
  modified: number;
  extension: string;
  hasAnalysis: boolean;
  analysis: DocumentAnalysis | null;
}

export interface DocumentAnalysis {
  jd_area: string;
  jd_category: string;
  document_type: string;
  issuer: string;
  subject_person?: string | null;
  tags: string[];
  confidence: 'high' | 'medium' | 'low';
  summary: string;
  date_mentioned?: string | null;
  entities: string[];
  extracted_text?: string;
  original_filename?: string;
  analyzed_at?: string;
}

// =============================================================================
// Johnny.Decimal Types
// =============================================================================

export interface JDCategory {
  name: string;
  keywords: string[];
}

export interface JDArea {
  name: string;
  categories: JDCategory[];
}

// =============================================================================
// Settings Types
// =============================================================================

export interface AppSettings {
  output_dir: string;
  inbox_dir: string;
  ai_provider: string;
  effective_provider: string;
  setup_complete: boolean;
  anthropic_model: string;
  openai_model: string;
  ollama_url: string;
  ollama_model: string;
  has_anthropic_key: boolean;
  has_openai_key: boolean;
  has_keychain_support: boolean;
}

// =============================================================================
// IPC Request/Response Types
// =============================================================================

export interface IPCRequest {
  id: string;
  method: string;
  params: Record<string, unknown>;
}

export interface IPCResponse<T = unknown> {
  id: string;
  result: T | null;
  error: string | null;
}

// =============================================================================
// Method-specific Request/Response Types
// =============================================================================

// files:list
export interface FilesListParams {
  folder: string;
  recursive?: boolean;
}

export interface FilesListResult {
  files: FileEntry[];
  count: number;
}

// files:analyze
export interface FilesAnalyzeParams {
  filePath: string;
  force?: boolean;
  folderHint?: string;
}

export interface FilesAnalyzeResult {
  success: boolean;
  cached: boolean;
  analysis: DocumentAnalysis;
}

// files:move
export interface FilesMoveParams {
  filePath: string;
  area: string;
  category: string;
}

export interface FilesMoveResult {
  success: boolean;
  destination: string;
  analysis: DocumentAnalysis;
}

// files:delete
export interface FilesDeleteParams {
  filePath: string;
}

export interface FilesDeleteResult {
  success: boolean;
  deleted: string;
}

// settings:get
export type SettingsGetResult = AppSettings;

// settings:set
export interface SettingsSetParams {
  key: string;
  value: unknown;
}

export interface SettingsSetResult {
  success: boolean;
  key: string;
}

// jd:getAreas
export interface JDGetAreasResult {
  areas: JDArea[];
}

// =============================================================================
// IPC Channel Names
// =============================================================================

export const IPC_CHANNELS = {
  // File operations
  FILES_LIST: 'files:list',
  FILES_ANALYZE: 'files:analyze',
  FILES_MOVE: 'files:move',
  FILES_DELETE: 'files:delete',

  // Settings
  SETTINGS_GET: 'settings:get',
  SETTINGS_SET: 'settings:set',

  // JD System
  JD_GET_AREAS: 'jd:getAreas',

  // Thumbnails (handled in main process)
  THUMBNAILS_GENERATE: 'thumbnails:generate',

  // Python bridge status
  PYTHON_STATUS: 'python:status',
  PYTHON_RESTART: 'python:restart',
} as const;

export type IPCChannel = (typeof IPC_CHANNELS)[keyof typeof IPC_CHANNELS];

// =============================================================================
// Error Types
// =============================================================================

export class PythonBridgeError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly details?: unknown
  ) {
    super(message);
    this.name = 'PythonBridgeError';
  }
}

// =============================================================================
// Event Types
// =============================================================================

export interface PythonStatusEvent {
  status: 'starting' | 'ready' | 'error' | 'stopped';
  message?: string;
}
