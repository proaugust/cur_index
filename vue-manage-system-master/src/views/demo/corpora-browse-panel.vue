<template>
    <el-card v-if="canShow" shadow="hover" class="corpora-browse">
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
            <el-tag size="small" type="info">512d · BGE</el-tag>
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
            <el-form-item :label="t('pages.rag.corporaBrowse.corpusName')" required>
                <el-input v-model="form.corpus_name" clearable style="width: 280px" />
            </el-form-item>
            <el-form-item v-if="mode !== 'llm'" :label="t('pages.rag.corporaBrowse.sourceFile')">
                <el-input
                    v-model="form.source_file"
                    clearable
                    :placeholder="t('pages.rag.corporaBrowse.sourceFilePh')"
                    style="width: 280px"
                />
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
                <el-button type="primary" :loading="loading" @click="runQuery">
                    {{ t('pages.rag.corporaBrowse.submit') }}
                </el-button>
                <el-popconfirm
                    v-if="canClear"
                    :title="clearConfirmTitle"
                    width="320"
                    :confirm-button-text="t('pages.rag.corporaBrowse.clear')"
                    :cancel-button-text="t('common.cancel')"
                    @confirm="clearCorpusData"
                >
                    <template #reference>
                        <el-button type="danger" plain :loading="clearing">
                            {{ t('pages.rag.corporaBrowse.clear') }}
                        </el-button>
                    </template>
                </el-popconfirm>
            </el-form-item>
        </el-form>
        <div v-if="polishedAnswer" class="answer-box">
            <div class="answer-label">{{ t('pages.rag.highlights.polished_answer') }}</div>
            <div class="answer-body">{{ polishedAnswer }}</div>
        </div>
        <el-table v-if="rows.length" :data="pagedRows" stripe border size="small" class="result-table">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="source_file" :label="t('pages.rag.columns.source_file')" min-width="120" show-overflow-tooltip />
            <el-table-column prop="section_title" :label="t('pages.rag.columns.section_title')" min-width="100" show-overflow-tooltip />
            <el-table-column prop="similarity" :label="t('pages.rag.columns.similarity')" width="90" />
            <el-table-column prop="chunk_index" :label="t('pages.rag.columns.chunk_index')" width="70" />
            <el-table-column prop="char_count" :label="t('pages.rag.columns.char_count')" width="80" />
            <el-table-column prop="embedding_preview" :label="t('pages.rag.columns.embedding_preview')" min-width="160" show-overflow-tooltip />
            <el-table-column
                prop="content"
                :label="t('pages.rag.columns.content')"
                min-width="420"
                :show-overflow-tooltip="contentTooltip"
            />
        </el-table>
        <el-pagination
            v-if="rows.length > pageSize"
            class="pager"
            layout="prev, pager, next, total"
            :total="rows.length"
            :page-size="pageSize"
            v-model:current-page="page"
        />
        <el-empty v-else-if="queried && !rows.length && !polishedAnswer" :description="t('pages.rag.corporaBrowse.empty')" />
    </el-card>
</template>

<script setup lang="ts" name="corpora-browse-panel">
import { computed, reactive, ref, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { useI18n } from 'vue-i18n';
import { clearCorpus, searchCorpus, searchCorpusAndLlm } from '@/api';
import FeatureIntroIcon from '@/components/feature-intro-icon.vue';
import type { FeatureIntroMap } from '@/composables/useFeatureIntros';
import { usePermissStore } from '@/store/permiss';

type Mode = 'search' | 'llm';
type Row = Record<string, unknown>;

defineProps<{ introPageKey?: string; intros?: FeatureIntroMap }>();
const emit = defineEmits<{ 'intro-saved': [sectionKey: string, content: string] }>();

const { t } = useI18n();
const permiss = usePermissStore();
const canSearch = computed(() => permiss.hasApi('82', 'corpora-search'));
const canLlm = computed(() => permiss.hasApi('82', 'corpora-search-llm'));
const canClear = computed(() => permiss.hasApi('82', 'corpora-clear'));
const canShow = computed(() => canSearch.value || canLlm.value);

const mode = ref<Mode>('search');
const loading = ref(false);
const clearing = ref(false);
const queried = ref(false);
const rows = ref<Row[]>([]);
const polishedAnswer = ref('');
const page = ref(1);
const pageSize = 10;
const form = reactive({
    corpus_name: 'fastapi',
    source_file: '',
    q: '',
    limit: 5,
    min_similarity: 0.55,
    retrieve_mode: 'hybrid',
    expand_parent: true,
});

watch(
    () => [canSearch.value, canLlm.value] as const,
    () => {
        if (mode.value === 'search' && !canSearch.value) mode.value = 'llm';
        else if (mode.value === 'llm' && !canLlm.value) mode.value = 'search';
    },
    { immediate: true },
);
watch(mode, () => { page.value = 1; });

const pagedRows = computed(() => rows.value.slice((page.value - 1) * pageSize, page.value * pageSize));

/** 悬停显示全文（多行、可滚动、可移入复制） */
const contentTooltip = {
    popperClass: 'corpus-content-tooltip',
    placement: 'top' as const,
    enterable: true,
};

const clearConfirmTitle = computed(() => {
    const name = form.corpus_name.trim() || '—';
    return t('pages.rag.corporaBrowse.clearConfirm', { name });
});

const errDetail = (err: unknown) =>
    err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;

const runQuery = async () => {
    const name = form.corpus_name.trim();
    if (!name) {
        ElMessage.warning(t('pages.rag.corporaBrowse.corpusRequired'));
        return;
    }
    loading.value = true;
    queried.value = true;
    polishedAnswer.value = '';
    rows.value = [];
    page.value = 1;
    try {
        if (mode.value === 'search') {
            const res = await searchCorpus({
                corpus_name: name,
                q: form.q.trim() || undefined,
                limit: form.limit,
                min_similarity: form.min_similarity,
                source_file: form.source_file.trim() || undefined,
                retrieve_mode: form.retrieve_mode,
            });
            rows.value = (res.data as Row[]) ?? [];
        } else {
            const res = await searchCorpusAndLlm({
                corpus_name: name,
                q: form.q.trim() || undefined,
                limit: form.limit,
                min_similarity: form.min_similarity,
                retrieve_mode: form.retrieve_mode,
                expand_parent: form.expand_parent,
            });
            const data = res.data as { polished_answer?: string; original_sources?: Row[] };
            polishedAnswer.value = data.polished_answer ?? '';
            rows.value = data.original_sources ?? [];
        }
    } catch (err: unknown) {
        ElMessage.error(errDetail(err) || t('pages.rag.corporaBrowse.failed'));
    } finally {
        loading.value = false;
    }
};

const clearCorpusData = async () => {
    const name = form.corpus_name.trim();
    if (!name) {
        ElMessage.warning(t('pages.rag.corporaBrowse.corpusRequired'));
        return;
    }
    clearing.value = true;
    try {
        const res = await clearCorpus({ corpus_name: name });
        const deleted = (res.data as { deleted_chunks?: number })?.deleted_chunks ?? 0;
        rows.value = [];
        polishedAnswer.value = '';
        queried.value = false;
        ElMessage.success(t('pages.rag.corporaBrowse.clearDone', { count: deleted }));
    } catch (err: unknown) {
        ElMessage.error(errDetail(err) || t('pages.rag.corporaBrowse.clearFailed'));
    } finally {
        clearing.value = false;
    }
};
</script>

<style scoped>
.corpora-browse { margin-bottom: 16px; }
.panel-title-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.panel-title { font-size: 16px; font-weight: 600; }
.panel-desc { margin: 0 0 12px; color: #909399; font-size: 13px; }
.param-form { max-width: 720px; }
.answer-box { margin: 12px 0; padding: 12px 14px; background: #f5f7fa; border-radius: 6px; }
.answer-label { font-size: 13px; color: #606266; margin-bottom: 6px; }
.answer-body { white-space: pre-wrap; line-height: 1.6; font-size: 14px; }
.result-table { width: 100%; margin-top: 8px; }
.pager { margin-top: 12px; justify-content: flex-end; }
</style>

<!-- tooltip 挂到 body，需非 scoped -->
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
