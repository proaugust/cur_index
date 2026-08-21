<template>
    <div v-if="canImport" class="corpora-import">
        <div class="panel-title-row">
            <span class="panel-title">{{ t('pages.rag.corporaImportPanel.title') }}</span>
            <FeatureIntroIcon
                v-if="introPageKey"
                :page-key="introPageKey"
                section-key="corpora-import"
                :intros="intros"
                :title="t('pages.rag.corporaImportPanel.title')"
                @saved="(key, content) => emit('intro-saved', key, content)"
            />
            <el-tag size="small" type="info">.md / .zip</el-tag>
        </div>
        <p class="panel-desc">{{ t('pages.rag.corporaImportPanel.description') }}</p>
        <el-form label-width="110px" class="param-form" @submit.prevent>
            <el-form-item :label="t('pages.rag.corporaImportPanel.corpusName')" required>
                <el-input
                    v-model="form.corpus_name"
                    clearable
                    :placeholder="t('pages.rag.corporaImportPanel.corpusNamePh')"
                    style="width: 280px"
                    @input="onNameInput"
                />
            </el-form-item>
            <el-form-item :label="t('pages.rag.corporaImportPanel.category')">
                <el-select v-model="form.category" filterable style="width: 280px">
                    <el-option v-for="c in categories" :key="c.value" :label="c.label" :value="c.value" />
                </el-select>
            </el-form-item>
            <el-form-item :label="t('pages.rag.corporaImportPanel.file')" required>
                <el-upload
                    :auto-upload="false"
                    :limit="1"
                    accept=".md,.markdown,.txt,.zip"
                    :on-change="onFileChange"
                    :on-remove="onFileRemove"
                >
                    <el-button>{{ t('pages.rag.corporaImportPanel.pickFile') }}</el-button>
                </el-upload>
            </el-form-item>
            <el-form-item :label="t('pages.rag.corporaImportPanel.replace')">
                <el-switch v-model="form.replace_existing" />
            </el-form-item>
            <el-form-item :label="t('pages.rag.corporaImportPanel.chunkStrategy')">
                <el-select v-model="form.chunk_strategy" style="width: 180px">
                    <el-option label="structure" value="structure" />
                    <el-option label="legacy" value="legacy" />
                </el-select>
            </el-form-item>
            <el-form-item :label="t('pages.rag.corporaImportPanel.maxChunk')">
                <el-input-number v-model="form.max_chunk_len" :min="50" :max="2000" />
            </el-form-item>
            <el-form-item :label="t('pages.rag.corporaImportPanel.minChunk')">
                <el-input-number v-model="form.min_chunk_len" :min="20" :max="1000" />
            </el-form-item>
            <el-form-item :label="t('pages.rag.corporaImportPanel.overlap')">
                <el-input-number v-model="form.chunk_overlap" :min="0" :max="500" />
            </el-form-item>
            <el-form-item>
                <el-button type="primary" :loading="loading" @click="submit">
                    {{ t('pages.rag.corporaImportPanel.submit') }}
                </el-button>
            </el-form-item>
        </el-form>
        <p v-if="progressText" class="progress">{{ progressText }}</p>
        <div v-if="lastResult" class="raw-block">
            <div class="answer-label">JSON</div>
            <el-input v-model="lastResult" type="textarea" :rows="10" readonly class="response-box" />
        </div>
    </div>
</template>

<script setup lang="ts" name="corpora-import-panel">
import { useI18n } from 'vue-i18n';
import FeatureIntroIcon from '@/components/feature-intro-icon.vue';
import type { FeatureIntroMap } from '@/composables/useFeatureIntros';
import { useCorporaImport } from '@/composables/useCorporaImport';

defineProps<{ introPageKey?: string; intros?: FeatureIntroMap }>();
const emit = defineEmits<{ 'intro-saved': [sectionKey: string, content: string] }>();
const { t } = useI18n();
const {
    canImport,
    loading,
    categories,
    form,
    progressText,
    lastResult,
    onFileChange,
    onFileRemove,
    onNameInput,
    submit,
} = useCorporaImport();
</script>

<style scoped>
.corpora-import { margin-bottom: 0; }
.panel-title-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.panel-title { font-size: 16px; font-weight: 600; }
.panel-desc { margin: 0 0 12px; color: #909399; font-size: 13px; }
.param-form { max-width: 720px; }
.progress { margin: 8px 0; color: #606266; font-size: 13px; }
.raw-block { margin-top: 12px; }
.answer-label { font-size: 13px; color: #606266; margin-bottom: 6px; }
.response-box { font-family: ui-monospace, Consolas, monospace; }
</style>
