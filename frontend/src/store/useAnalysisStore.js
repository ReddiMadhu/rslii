import { create } from "zustand";

const useAnalysisStore = create((set) => ({
  // Analysis results
  result: null,
  // Loading & error state
  isLoading: false,
  error: null,
  // Active tab
  activeTab: "summary",
  // Expanded node detail panels
  expandedNodes: new Set(),

  // Actions
  setResult: (result) => set({ result, error: null, isLoading: false, activeTab: "summary" }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error, result: null, isLoading: false }),
  setActiveTab: (activeTab) => set({ activeTab }),
  reset: () =>
    set({
      result: null,
      isLoading: false,
      error: null,
      activeTab: "summary",
      expandedNodes: new Set(),
    }),

  toggleNodeExpanded: (nodeId) =>
    set((state) => {
      const next = new Set(state.expandedNodes);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return { expandedNodes: next };
    }),
}));

export default useAnalysisStore;
