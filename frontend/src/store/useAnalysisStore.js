import { create } from "zustand";

export const APP_STATES = {
  LANDING: "landing",
  UPLOAD_SCRIPT: "upload_script",
  SOURCE_MAPPING: "source_mapping",
  EXECUTING: "executing",
  RESULTS: "results",
};

const useAnalysisStore = create((set) => ({
  appState: APP_STATES.LANDING,
  parseResult: null,
  pipelineCode: "",
  pipelineFilename: null,
  fileMappings: {},
  enableLlmForExecute: true,
  executionProgress: {},
  liveExecSummary: null,
  execLog: [],
  result: null,
  isLoading: false,
  error: null,
  activeTab: "summary",
  expandedNodes: new Set(),
  selectedDetailNode: null,
  detailPanelOpen: false,
  // Column lineage trace state
  columnTraceColumn: null,
  columnTraceDirection: "downstream",
  columnTraceData: null,
  columnTraceExpanded: new Set(),

  setAppState: (appState) => set({ appState }),
  setParsed: (parseResult, code, filename) =>
    set({
      parseResult,
      pipelineCode: code,
      pipelineFilename: filename,
      appState: APP_STATES.SOURCE_MAPPING,
      error: null,
      isLoading: false,
      fileMappings: {},
      executionProgress: {},
      liveExecSummary: null,
      execLog: [],
      result: null,
    }),
  setFileMapping: (sourceId, file) =>
    set((s) => ({
      fileMappings: { ...s.fileMappings, [sourceId]: file },
    })),
  clearFileMapping: (sourceId) =>
    set((s) => {
      const next = { ...s.fileMappings };
      delete next[sourceId];
      return { fileMappings: next };
    }),
  setEnableLlmForExecute: (v) => set({ enableLlmForExecute: !!v }),
  updateNodeProgress: (nodeId, update) =>
    set((s) => ({
      executionProgress: {
        ...s.executionProgress,
        [nodeId]: { ...(s.executionProgress[nodeId] || {}), ...update },
      },
    })),
  appendExecLog: (text) =>
    set((s) => ({
      execLog: [...s.execLog, { t: Date.now(), text: String(text) }].slice(-400),
    })),
  clearExecLog: () => set({ execLog: [] }),
  setResult: (result) =>
    set({
      result,
      error: null,
      isLoading: false,
      appState: APP_STATES.RESULTS,
      activeTab: "summary",
      executionProgress: {},
      liveExecSummary: null,
      execLog: [],
    }),
  setLiveExecSummary: (liveExecSummary) => set({ liveExecSummary }),
  setExecuting: () =>
    set({
      appState: APP_STATES.EXECUTING,
      isLoading: false,
      error: null,
      activeTab: "lineage",
      executionProgress: {},
      liveExecSummary: null,
      execLog: [],
    }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error, isLoading: false }),
  setActiveTab: (activeTab) => set({ activeTab }),
  setSelectedDetailNode: (id) =>
    set({ selectedDetailNode: id, detailPanelOpen: id != null }),
  setDetailPanelOpen: (open) => set({ detailPanelOpen: open }),
  // Column lineage trace actions
  setColumnTrace: (column, direction) =>
    set({ columnTraceColumn: column, columnTraceDirection: direction, columnTraceData: null }),
  setColumnTraceData: (data) => set({ columnTraceData: data }),
  resetColumnTrace: () =>
    set({ columnTraceColumn: null, columnTraceData: null, columnTraceExpanded: new Set() }),
  toggleColumnTraceExpanded: (nodeId) =>
    set((state) => {
      const next = new Set(state.columnTraceExpanded);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return { columnTraceExpanded: next };
    }),
  reset: () =>
    set({
      appState: APP_STATES.UPLOAD_SCRIPT,
      parseResult: null,
      pipelineCode: "",
      pipelineFilename: null,
      fileMappings: {},
      enableLlmForExecute: true,
      executionProgress: {},
      liveExecSummary: null,
      execLog: [],
      result: null,
      isLoading: false,
      error: null,
      activeTab: "summary",
      expandedNodes: new Set(),
      selectedDetailNode: null,
      detailPanelOpen: false,
      columnTraceColumn: null,
      columnTraceDirection: "downstream",
      columnTraceData: null,
      columnTraceExpanded: new Set(),
    }),
  toggleNodeExpanded: (nodeId) =>
    set((state) => {
      const next = new Set(state.expandedNodes);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return { expandedNodes: next };
    }),
}));

export default useAnalysisStore;
