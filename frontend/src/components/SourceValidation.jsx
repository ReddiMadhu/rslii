import { useCallback, useMemo, useState } from "react";
import { ArrowLeft, Play, Loader2, FileCheck } from "lucide-react";
import useAnalysisStore, { APP_STATES } from "../store/useAnalysisStore";
import ValidationKeyFindings from "./ValidationKeyFindings";
import ValidationKeyAlerts from "./ValidationKeyAlerts";
import ValidationRowStats from "./ValidationRowStats";
import ValidationSampleData from "./ValidationSampleData";
import ValidationAdditionalColumns from "./ValidationAdditionalColumns";
import ValidationMissingColumns from "./ValidationMissingColumns";
import ValidationDtypeChanges from "./ValidationDtypeChanges";
import ValidationExecuteConfirm from "./ValidationExecuteConfirm";
import { buildFixSummary, runPipelineExecution } from "../lib/executePipeline";

function FileSection({ sourceId, data, onSectionSave, sectionSaved }) {
  const mark = (section) => onSectionSave(sourceId, section);

  return (
    <details
      open
      className="rounded-2xl overflow-hidden mb-4"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
    >
      <summary
        className="cursor-pointer px-4 py-3 text-sm font-bold flex items-center gap-2 list-none"
        style={{ color: "var(--text-primary)" }}
      >
        <FileCheck size={16} style={{ color: "var(--primary)" }} />
        {data.filename || sourceId}
        {data.llm_used && (
          <span className="text-[10px] font-normal px-2 py-0.5 rounded-full" style={{ background: "rgba(168,85,247,0.15)", color: "#a855f7" }}>
            AI
          </span>
        )}
      </summary>
      <div className="px-4 pb-4 space-y-5">
        <ValidationKeyFindings findings={data.key_findings} />
        <ValidationRowStats
          rowCount={data.row_count}
          columnCount={data.column_count}
          nullBlankColumns={data.null_blank_columns}
        />
        <ValidationSampleData sampleData={data.sample_data} columns={data.columns} />
        <ValidationKeyAlerts alerts={data.key_alerts} />
        <ValidationAdditionalColumns
          columns={data.additional_columns}
          hasPreviousSnapshot={data.has_previous_snapshot}
          onSave={() => mark("additional")}
          saved={sectionSaved[`${sourceId}:additional`]}
        />
        <ValidationMissingColumns
          sourceId={sourceId}
          rows={data.missing_columns}
          additionalColumns={data.additional_columns}
          fuzzyNote={data.fuzzy_fallback_note}
          hasPreviousSnapshot={data.has_previous_snapshot}
          onSave={() => mark("missing")}
          saved={sectionSaved[`${sourceId}:missing`]}
        />
        <ValidationDtypeChanges
          sourceId={sourceId}
          changes={data.dtype_changes}
          hasPreviousSnapshot={data.has_previous_snapshot}
          onSave={() => mark("dtype")}
          saved={sectionSaved[`${sourceId}:dtype`]}
        />
      </div>
    </details>
  );
}

export default function SourceValidation({ llmAvailable = false }) {
  const parseResult = useAnalysisStore((s) => s.parseResult);
  const pipelineCode = useAnalysisStore((s) => s.pipelineCode);
  const pipelineFilename = useAnalysisStore((s) => s.pipelineFilename);
  const fileMappings = useAnalysisStore((s) => s.fileMappings);
  const validationResult = useAnalysisStore((s) => s.validationResult);
  const validationLoading = useAnalysisStore((s) => s.validationLoading);
  const validationOverrides = useAnalysisStore((s) => s.validationOverrides);
  const validationSectionSaved = useAnalysisStore((s) => s.validationSectionSaved);
  const enableLlmForExecute = useAnalysisStore((s) => s.enableLlmForExecute);
  const setAppState = useAnalysisStore((s) => s.setAppState);
  const setExecuting = useAnalysisStore((s) => s.setExecuting);
  const setError = useAnalysisStore((s) => s.setError);
  const setLiveExecSummary = useAnalysisStore((s) => s.setLiveExecSummary);
  const markValidationSectionSaved = useAnalysisStore((s) => s.markValidationSectionSaved);

  const [showConfirm, setShowConfirm] = useState(false);

  const required = useMemo(
    () => (parseResult?.sources || []).filter((s) => s.requires_upload),
    [parseResult]
  );

  const fileEntries = useMemo(() => {
    const files = validationResult?.files || {};
    return Object.entries(files);
  }, [validationResult]);

  const fixSummary = useMemo(
    () => buildFixSummary(validationOverrides, validationResult),
    [validationOverrides, validationResult]
  );

  const handleExecute = useCallback(() => {
    setShowConfirm(true);
  }, []);

  const confirmExecute = useCallback(() => {
    setShowConfirm(false);
    runPipelineExecution({
      pipelineCode,
      pipelineFilename,
      fileMappings,
      required,
      enableLlmForExecute,
      overrides: validationOverrides,
      setExecuting,
      setError,
      setAppState,
      setLiveExecSummary,
    });
  }, [
    pipelineCode,
    pipelineFilename,
    fileMappings,
    required,
    enableLlmForExecute,
    validationOverrides,
    setExecuting,
    setError,
    setAppState,
    setLiveExecSummary,
  ]);

  if (validationLoading) {
    return (
      <div className="w-full max-w-4xl mx-auto flex flex-col items-center justify-center py-24 gap-4 animate-fade-in">
        <Loader2 size={32} className="animate-spin" style={{ color: "var(--primary)" }} />
        <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
          Analyzing source data…
        </p>
        {enableLlmForExecute && llmAvailable && (
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            Running AI analysis…
          </p>
        )}
      </div>
    );
  }

  if (!validationResult) {
    return (
      <div className="text-center py-12 text-sm" style={{ color: "var(--text-muted)" }}>
        No validation data. Return to source mapping.
      </div>
    );
  }

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6 animate-fade-in pb-8">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
          Source Validation
        </h2>
      </div>

      {fileEntries.map(([sourceId, data]) => (
        <FileSection
          key={sourceId}
          sourceId={sourceId}
          data={data}
          onSectionSave={markValidationSectionSaved}
          sectionSaved={validationSectionSaved}
        />
      ))}

      <div className="flex items-center justify-between pt-2">
        <button
          type="button"
          onClick={() => setAppState(APP_STATES.SOURCE_MAPPING)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}
        >
          <ArrowLeft size={16} />
          Back
        </button>
        <button
          type="button"
          onClick={handleExecute}
          className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-bold text-white"
          style={{ background: "linear-gradient(135deg, var(--primary), var(--primary-dark))" }}
        >
          <Play size={16} />
          Execute Pipeline
        </button>
      </div>

      {showConfirm && (
        <ValidationExecuteConfirm
          fixes={fixSummary}
          onCancel={() => setShowConfirm(false)}
          onConfirm={confirmExecute}
        />
      )}
    </div>
  );
}
