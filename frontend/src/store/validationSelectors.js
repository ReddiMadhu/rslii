import { useCallback } from "react";
import useAnalysisStore from "./useAnalysisStore";
import { EMPTY_SOURCE_OVERRIDES } from "./validationOverridesUtil";

/** Hook with a stable selector reference (required for useSyncExternalStore). */
export function useSourceOverrides(sourceId) {
  const selector = useCallback(
    (state) => state.validationOverrides[sourceId] ?? EMPTY_SOURCE_OVERRIDES,
    [sourceId]
  );
  return useAnalysisStore(selector);
}
