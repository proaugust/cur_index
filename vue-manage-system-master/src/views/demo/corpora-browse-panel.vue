<template>
    <div v-if="canShow" class="corpora-browse">
        <div class="panel-title-row">
            <span class="panel-title">{{ t('pages.rag.corporaBrowse.title') }}</span>
            <FeatureIntroIcon
                v-if="introPageKey"
                :page-key="introPageKey"
                section-key="corpora-browse"
                :intros="intros"
                :title="t('pages.rag.corporaBrowse.title')"
                @saved="(key, content) => emit('intro-saved', key, content)"
            />
            <el-tag size="small" type="info">768d · BGE</el-tag>
        </div>
        <p class="panel-desc">{{ t('pages.rag.corporaBrowse.description') }}</p>
        <el-form label-width="100px" class="param-form" @submit.prevent>
            <el-form-item :label="t('pages.rag.corporaBrowse.mode')" required>
                <el-radio-group v-model="mode">
                    <el-radio-button v-if="canSearch" value="search">
                        {{ t('pages.rag.corporaBrowse.modeSearch') }}
                    </el-radio-button>
                    <el-radio-button v-if="canLlm" value="llm">
                        {{ t('pages.rag.corporaBrowse.modeLlm') }}
                    </el-radio-button>
                </el-radio-group>
            </el-form-item>
            <el-form-item :label="t('pages.rag.corporaBrowse.query')">
                <el-input
                    v-model="form.q"
                    clearable
                    type="textarea"
                    :rows="2"
                    :placeholder="t('pages.rag.corporaBrowse.queryPh')"
                    style="max-width: 560px"
                />
            </el-form-item>
            <el-form-item :label="t('pages.rag.corporaBrowse.category')">
                <el-select
                    v-model="form.categories"
                    multiple
                    clearable
                    filterable
                    collapse-tags
                    collapse-tags-tooltip
                    style="width: 360px"
                    :placeholder="t('pages.rag.corporaBrowse.categoryPh')"
                    @change="onCategoryChange"
                >
                    <el-option v-for="c in categories" :key="c.value" :label="c.label" :value="c.value" />
                </el-select>
            </el-form-item>
            <el-form-item :label="t('pages.rag.corporaBrowse.corpusName')">
                <el-select
                    v-model="form.corpus_names"
                    multiple
                    filterable
                    clearable
                    collapse-tags
                    collapse-tags-tooltip
                    style="width: 360px"
                    :placeholder="t('pages.rag.corporaBrowse.corpusPh')"
                    :loading="corporaLoading"
                >
                    <el-option v-for="c in corpora" :key="c.name" :label="c.name" :value="c.name" />
                </el-select>
            </el-form-item>
            <el-form-item :label="t('pages.rag.corporaBrowse.sourceFile')">
                <el-input
                    v-model="form.source_file"
                    clearable
                    :placeholder="t('pages.rag.corporaBrowse.sourceFilePh')"
                    style="width: 360px"
                />
            </el-form-item>
            <el-form-item v-if="filterRationale" :label="t('pages.rag.corporaBrowse.suggestHint')">
                <span class="rationale">{{ filterRationale }}</span>
            </el-form-item>
            <el-form-item :label="t('pages.rag.corporaBrowse.limit')">
                <el-input-number v-model="form.limit" :min="1" :max="50" />
            </el-form-item>
            <el-form-item :label="t('pages.rag.corporaBrowse.minSimilarity')">
                <el-input-number v-model="form.min_similarity" :min="0" :max="1" :step="0.05" />
            </el-form-item>
            <el-form-item label="检索模式">
                <el-select v-model="form.retrieve_mode" style="width: 220px">
                    <el-option label="hybrid（向量+全文+C1）" value="hybrid" />
                    <el-option label="vector（仅向量）" value="vector" />
                    <el-option label="hybrid_rerank（同 hybrid）" value="hybrid_rerank" />
                </el-select>
            </el-form-item>
            <el-form-item v-if="mode === 'llm'" label="扩 Parent">
                <el-switch v-model="form.expand_parent" />
            </el-form-item>
            <el-form-item>
                <el-button :loading="suggestLoading" :disabled="!form.q.trim()" @click="suggestFilters">
                    {{ t('pages.rag.corporaBrowse.suggestFilters') }}
                </el-button>
                <el-button type="primary" :loading="loading" @click="runQuery">
                    {{ t('pages.rag.corporaBrowse.submit') }}
                </el-button>
            </el-form-item>
        </el-form>
        <div v-if="polishedAnswer" class="answer-box">
            <div class="answer-label">{{ t('pages.rag.highlights.polished_answer') }}</div>
            <div class="answer-body">{{ polishedAnswer }}</div>
        </div>
        <el-table v-if="rows.length" :data="pagedRows" stripe border size="small" class="result-table">
            <el-table-column prop="id" label="ID" min-width="64" />
            <el-table-column prop="source_file" :label="t('pages.rag.columns.source_file')" min-width="100" show-overflow-tooltip />
            <el-table-column prop="section_title" :label="t('pages.rag.columns.section_title')" min-width="90" show-overflow-tooltip />
            <el-table-column prop="similarity" :label="t('pages.rag.columns.similarity')" min-width="72" />
            <el-table-column prop="chunk_index" :label="t('pages.rag.columns.chunk_index')" min-width="56" />
            <el-table-column prop="lang" :label="t('pages.rag.columns.lang')" min-width="56" />
            <el-table-column prop="embedding_preview" :label="t('pages.rag.columns.embedding_preview')" min-width="100" show-overflow-tooltip />
        </el-table>
        <el-pagination
            v-if="rows.length > pageSize"
            class="pager"
            layout="prev, pager, next, total"
            :total="rows.length"
            :page-size="pageSize"
            v-model:current-page="page"
        />
        <el-empty
            v-else-if="queried && !rows.length && !polishedAnswer"
            :description="t('pages.rag.corporaBrowse.empty')"
        />
        <div v-if="lastQuery" class="raw-block">
            <div class="answer-label">原始查询</div>
            <pre class="raw-pre">{{ lastQuery }}</pre>
        </div>
        <div v-if="lastJson" class="raw-block">
            <div class="answer-label">JSON</div>
            <el-input v-model="lastJson" type="textarea" :rows="12" readonly class="response-box" />
        </div>
    </div>
</template>

<script setup lang="ts" name="corpora-browse-panel">
import { useI18n } from 'vue-i18n';
import FeatureIntroIcon from '@/components/feature-intro-icon.vue';
import type { FeatureIntroMap } from '@/composables/useFeatureIntros';
import { useCorporaBrowse } from '@/composables/useCorporaBrowse';

defineProps<{ introPageKey?: string; intros?: FeatureIntroMap }>();
const emit = defineEmits<{ 'intro-saved': [sectionKey: string, content: string] }>();
const { t } = useI18n();
const {
    canShow,
    canSearch,
    canLlm,
    mode,
    loading,
    suggestLoading,
    corporaLoading,
    queried,
    rows,
    polishedAnswer,
    filterRationale,
    page,
    pageSize,
    categories,
    corpora,
    form,
    pagedRows,
    lastQuery,
    lastJson,
    onCategoryChange,
    suggestFilters,
    runQuery,
} = useCorporaBrowse();
</script>

<style scoped>
.corpora-browse { margin-bottom: 0; }
.panel-title-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.panel-title { font-size: 16px; font-weight: 600; }
.panel-desc { margin: 0 0 12px; color: #909399; font-size: 13px; }
.param-form { max-width: 720px; }
.rationale { color: #606266; font-size: 13px; line-height: 1.5; }
.answer-box { margin: 12px 0; padding: 12px 14px; background: #f5f7fa; border-radius: 6px; }
.answer-label { font-size: 13px; color: #606266; margin-bottom: 6px; }
.answer-body { white-space: pre-wrap; word-break: break-word; line-height: 1.6; font-size: 14px; }
.result-table { width: 100%; margin-top: 8px; }
.raw-block { margin-top: 16px; }
.raw-pre {
    margin: 0;
    padding: 12px 14px;
    background: #f5f7fa;
    border-radius: 6px;
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 13px;
    line-height: 1.5;
}
.response-box { font-family: ui-monospace, Consolas, monospace; }
.result-table :deep(.el-table__header),
.result-table :deep(.el-table__body),
.result-table :deep(table) {
    table-layout: auto !important;
    width: 100% !important;
}
.result-table :deep(.el-table__cell) { text-align: left; }
.result-table :deep(th),
.result-table :deep(td) { white-space: nowrap; }
.result-table :deep(th .cell),
.result-table :deep(td .cell) { white-space: nowrap; }
.pager { margin-top: 12px; justify-content: flex-end; }
</style>

<style>
.corpus-content-tooltip {
    max-width: min(840px, 90vw) !important;
    max-height: 60vh;
    overflow: auto;
    white-space: pre-wrap !important;
    word-break: break-word;
    line-height: 1.55;
    font-size: 13px;
}
</style>
