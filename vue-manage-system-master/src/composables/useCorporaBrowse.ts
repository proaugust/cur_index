/** 业务资料库 Browse：分类 → 选库 → 检索 */
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { useI18n } from 'vue-i18n';
import {
    listCorpora,
    listCorpusCategories,
    searchCorpus,
    searchCorpusAndLlm,
    suggestCorpusCategory,
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
    const corporaLoading = ref(false);
    const queried = ref(false);
    const rows = ref<Row[]>([]);
    const polishedAnswer = ref('');
    const lastQuery = ref('');
    const lastJson = ref('');
    const page = ref(1);
    const pageSize = 10;
    const categories = ref<Cat[]>([]);
    const corpora = ref<Corpus[]>([]);
    const form = reactive({
        category: '',
        corpus_name: '',
        source_file: '',
        q: '',
        limit: 5,
        min_similarity: 0.55,
        retrieve_mode: 'hybrid',
        expand_parent: true,
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
            const res = await listCorpora(form.category ? { category: form.category } : undefined);
            corpora.value = (res.data as Corpus[]) ?? [];
            if (form.corpus_name && !corpora.value.some((c) => c.name === form.corpus_name)) {
                form.corpus_name = '';
            }
            if (!form.corpus_name && corpora.value.length === 1) {
                form.corpus_name = corpora.value[0].name;
            }
        } catch {
            corpora.value = [];
        } finally {
            corporaLoading.value = false;
        }
    };

    const onCategoryChange = () => {
        form.corpus_name = '';
        loadCorpora();
    };

    const suggestCat = async () => {
        try {
            const res = await suggestCorpusCategory({ q: form.q.trim() });
            const data = res.data as { category?: string; label?: string };
            if (data.category) {
                form.category = data.category;
                ElMessage.success(
                    `${t('pages.rag.corporaBrowse.suggestCategory')}: ${data.label || data.category}`,
                );
                await loadCorpora();
            }
        } catch {
            ElMessage.error(t('pages.rag.corporaBrowse.failed'));
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
        const q = form.q.trim() || undefined;
        const payload =
            mode.value === 'search'
                ? {
                      corpus_name: name,
                      q,
                      limit: form.limit,
                      min_similarity: form.min_similarity,
                      source_file: form.source_file.trim() || undefined,
                      retrieve_mode: form.retrieve_mode,
                  }
                : {
                      corpus_name: name,
                      q,
                      limit: form.limit,
                      min_similarity: form.min_similarity,
                      retrieve_mode: form.retrieve_mode,
                      expand_parent: form.expand_parent,
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
        corporaLoading,
        queried,
        rows,
        polishedAnswer,
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
        suggestCat,
        runQuery,
    };
}
