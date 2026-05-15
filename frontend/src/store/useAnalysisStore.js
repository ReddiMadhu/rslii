import { create } from "zustand";
import { buildDefaultOverridesFromValidation } from "./validationOverridesUtil";

export const APP_STATES = {
  LANDING: "landing",
  UPLOAD_SCRIPT: "upload_script",
  SOURCE_MAPPING: "source_mapping",
  SOURCE_VALIDATION: "source_validation",
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
  columnTraceColumn: null,
  columnTraceDirection: "downstream",
  columnTraceData: null,
  columnTraceExpanded: new Set(),
  validationResult: null,
  validationOverrides: {},
  validationLoading: false,
  validationSectionSaved: {},

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
      validationResult: null,
      validationOverrides: {},
      validationLoading: false,
      validationSectionSaved: {},
    }),
  setFileMapping: (sourceId, file) =>
    set((s) => {
      const prev = s.fileMappings[sourceId];
      const nextOverrides = { ...s.validationOverrides };
      if (prev !== file) {
        delete nextOverrides[sourceId];
      }
      return {
        fileMappings: { ...s.fileMappings, [sourceId]: file },
        validationOverrides: nextOverrides,
        validationResult: prev !== file ? null : s.validationResult,
      };
    }),
  clearFileMapping: (sourceId) =>
    set((s) => {
      const next = { ...s.fileMappings };
      delete next[sourceId];
      const nextOverrides = { ...s.validationOverrides };
      delete nextOverrides[sourceId];
      return {
        fileMappings: next,
        validationOverrides: nextOverrides,
        validationResult: null,
      };
    }),
  setEnableLlmForExecute: (v) => set({ enableLlmForExecute: !!v }),
  setValidationResult: (validationResult) =>
    set({
      validationResult,
      validationLoading: false,
      error: null,
      validationOverrides: buildDefaultOverridesFromValidation(validationResult),
    }),
  setValidationLoading: (validationLoading) => set({ validationLoading }),
  setValidationOverride: (sourceId, type, key, value) =>
    set((s) => {
      const cur = s.validationOverrides[sourceId] || {
        column_renames: {},
        dtype_casts: {},
        null_columns: [],
      };
      if (type === "null") {
        const set = new Set(cur.null_columns || []);
        if (value) set.add(key);
        else set.delete(key);
        return {
          validationOverrides: {
            ...s.validationOverrides,
            [sourceId]: { ...cur, null_columns: [...set] },
          },
        };
      }
      const bucket = type === "dtype" ? "dtype_casts" : "column_renames";
      const nextBucket = { ...cur[bucket] };
      if (value == null || value === "") {
        delete nextBucket[key];
      } else {
        nextBucket[key] = value;
      }
      return {
        validationOverrides: {
          ...s.validationOverrides,
          [sourceId]: { ...cur, [bucket]: nextBucket },
        },
      };
    }),
  clearValidationOverrides: () => set({ validationOverrides: {} }),
  markValidationSectionSaved: (sourceId, section) =>
    set((s) => ({
      validationSectionSaved: {
        ...s.validationSectionSaved,
        [`${sourceId}:${section}`]: true,
      },
    })),
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
  setError: (error) => set({ error, isLoading: false, validationLoading: false }),
  setActiveTab: (activeTab) => set({ activeTab }),
  setSelectedDetailNode: (id) =>
    set({ selectedDetailNode: id, detailPanelOpen: id != null }),
  setDetailPanelOpen: (open) => set({ detailPanelOpen: open }),
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
      validationResult: null,
      validationOverrides: {},
      validationLoading: false,
      validationSectionSaved: {},
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
