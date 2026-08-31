/** 业务资料库 Browse：分类多选 → 选库多选 → AI 建议过滤 → 检索 */
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { useI18n } from 'vue-i18n';
import {
    listCorpora,
    listCorpusCategories,
    searchCorpus,
    searchCorpusAndLlm,
    suggestCorpusSearchFilters,
} from '@/api';
import { usePermissStore } from '@/store/permiss';

export type BrowseMode = 'search' | 'llm';
type Row = Record<string, unknown>;
type Cat = { value: string; label: string };
type Corpus = { name: string; category?: string };

export function useCorporaBrowse() {
    const { t } = useI18n();
    const permiss = usePermissStore();
    const canSearch = computed(() => permiss.hasApi('82', 'corpora-search'));
    const canLlm = computed(() => permiss.hasApi('82', 'corpora-search-llm'));
    const canShow = computed(() => canSearch.value || canLlm.value);

    const mode = ref<BrowseMode>('search');
    const loading = ref(false);
    const suggestLoading = ref(false);
    const corporaLoading = ref(false);
    const queried = ref(false);
    const rows = ref<Row[]>([]);
    const polishedAnswer = ref('');
    const filterRationale = ref('');
    const lastQuery = ref('');
    const lastJson = ref('');
    const page = ref(1);
    const pageSize = 10;
    const categories = ref<Cat[]>([]);
    const allCorpora = ref<Corpus[]>([]);
    const form = reactive({
        categories: [] as string[],
        corpus_names: [] as string[],
        source_file: '',
        q: '',
        limit: 5,
        min_similarity: 0.35,
        retrieve_mode: 'hybrid',
        expand_parent: true,
    });

    const corpora = computed(() => {
        if (!form.categories.length) return allCorpora.value;
        const set = new Set(form.categories);
        return allCorpora.value.filter((c) => c.category && set.has(c.category));
    });

    const loadCategories = async () => {
        try {
            const res = await listCorpusCategories();
            categories.value = (res.data as Cat[]) ?? [];
        } catch {
            categories.value = [];
        }
    };

    const loadCorpora = async () => {
        corporaLoading.value = true;
        try {
            const res = await listCorpora();
            allCorpora.value = (res.data as Corpus[]) ?? [];
            pruneCorpusNames();
        } catch {
            allCorpora.value = [];
        } finally {
            corporaLoading.value = false;
        }
    };

    const pruneCorpusNames = () => {
        const allowed = new Set(corpora.value.map((c) => c.name));
        form.corpus_names = form.corpus_names.filter((n) => allowed.has(n));
    };

    const onCategoryChange = () => {
        pruneCorpusNames();
    };

    const suggestFilters = async () => {
        const q = form.q.trim();
        if (!q) {
            ElMessage.warning(t('pages.rag.corporaBrowse.queryRequired'));
            return;
        }
        suggestLoading.value = true;
        try {
            const res = await suggestCorpusSearchFilters({ q });
            const data = res.data as {
                categories?: string[];
                corpus_names?: string[];
                source_file?: string | null;
                retrieve_mode?: string;
                rationale?: string;
            };
            form.categories = data.categories ?? [];
            const allNames = new Set(allCorpora.value.map((c) => c.name));
            form.corpus_names = (data.corpus_names ?? []).filter((n) => allNames.has(n));
            if (data.source_file != null) form.source_file = data.source_file;
            if (data.retrieve_mode) form.retrieve_mode = data.retrieve_mode;
            filterRationale.value = data.rationale ?? '';
            ElMessage.success(t('pages.rag.corporaBrowse.suggestDone'));
        } catch {
            ElMessage.error(t('pages.rag.corporaBrowse.failed'));
        } finally {
            suggestLoading.value = false;
        }
    };

    onMounted(async () => {
        await loadCategories();
        await loadCorpora();
    });

    watch(
        () => [canSearch.value, canLlm.value] as const,
        () => {
            if (mode.value === 'search' && !canSearch.value) mode.value = 'llm';
            else if (mode.value === 'llm' && !canLlm.value) mode.value = 'search';
        },
        { immediate: true },
    );
    watch(mode, () => {
        page.value = 1;
    });

    const pagedRows = computed(() =>
        rows.value.slice((page.value - 1) * pageSize, page.value * pageSize),
    );

    const contentTooltip = {
        popperClass: 'corpus-content-tooltip',
        placement: 'top' as const,
        enterable: true,
    };

    const errDetail = (err: unknown) =>
        err && typeof err === 'object' && 'response' in err
            ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
            : undefined;

    const runQuery = async () => {
        if (loading.value) return;
        const sourceFile = form.source_file.trim();
        loading.value = true;
        queried.value = true;
        polishedAnswer.value = '';
        rows.value = [];
        page.value = 1;
        const q = form.q.trim() || undefined;
        const payload = {
            categories: form.categories.length ? form.categories.join(',') : undefined,
            corpus_names: form.corpus_names.length ? form.corpus_names.join(',') : undefined,
            q,
            limit: form.limit,
            min_similarity: form.min_similarity,
            retrieve_mode: form.retrieve_mode,
            ...(mode.value === 'search'
                ? { source_file: sourceFile || undefined }
                : { expand_parent: form.expand_parent, source_file: sourceFile || undefined }),
        };
        lastQuery.value = JSON.stringify(payload, null, 2);
        lastJson.value = '';
        try {
            if (mode.value === 'search') {
                const res = await searchCorpus(payload);
                rows.value = (res.data as Row[]) ?? [];
                lastJson.value = JSON.stringify(res.data ?? [], null, 2);
            } else {
                const res = await searchCorpusAndLlm(payload);
                const data = res.data as { polished_answer?: string; original_sources?: Row[] };
                polishedAnswer.value = data.polished_answer ?? '';
                rows.value = data.original_sources ?? [];
                lastJson.value = JSON.stringify(res.data ?? {}, null, 2);
            }
        } catch (err: unknown) {
            ElMessage.error(errDetail(err) || t('pages.rag.corporaBrowse.failed'));
        } finally {
            loading.value = false;
        }
    };

    return {
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
        contentTooltip,
        lastQuery,
        lastJson,
        onCategoryChange,
        suggestFilters,
        runQuery,
    };
}
