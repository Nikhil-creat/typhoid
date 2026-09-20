{{- define "typhoid.image" -}}
{{ .root.Values.global.imageRegistry }}/{{ .svc.image }}:{{ .svc.tag }}
{{- end }}
{{- define "typhoid.env" -}}
- { name: BUS_BACKEND,           value: {{ .Values.config.busBackend | quote }} }
- { name: WORKFLOW_ENGINE,       value: {{ .Values.config.workflowEngine | quote }} }
- { name: AUTONOMY_LEVEL,        value: {{ .Values.config.autonomyLevel | quote }} }
- { name: CHAOS_MAX_BLAST_RADIUS, value: {{ .Values.config.chaosMaxBlastRadius | quote }} }
- { name: CHAOS_ALLOW_PRODUCTION, value: {{ .Values.config.chaosAllowProduction | quote }} }
- { name: WORKER_TTL_SECONDS,    value: {{ .Values.config.workerTtlSeconds | quote }} }
- { name: WORKER_RUNTIME,        value: {{ .Values.agents.runtime | quote }} }
{{- end }}
