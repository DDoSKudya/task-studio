{{- define "task-studio.name" -}}
task-studio
{{- end -}}

{{- define "task-studio.fullname" -}}
{{ include "task-studio.name" . }}
{{- end -}}

{{- define "task-studio.labels" -}}
app.kubernetes.io/name: {{ include "task-studio.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "task-studio.selectorLabels" -}}
app.kubernetes.io/name: {{ include "task-studio.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "task-studio.image" -}}
{{ printf "%s/task-studio-%s:%s" .Values.imageRegistry .image .Values.imageTag }}
{{- end -}}
