/** 业务资料库：上传导入（异步 job 轮询）；资料名必填，默认取文件/文件夹名 */
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { useI18n } from 'vue-i18n';
import { getCorpusImportJob, importCorpus, listCorpusCategories } from '@/api';
import { usePermissStore } from '@/store/permiss';

type Cat = { value: string; label: string };
type JobStatus = {
    job_id: string;
    status: 'pending' | 'running' | 'done' | 'failed';
    corpus_name?: string;
    files_done?: number;
    files_total?: number;
    chunks?: number;
    error?: string | null;
};

const POLL_MS = 1500;
const TIMEOUT_MS = 600_000;

const fileStem = (name: string) => {
    const base = name.split(/[/\\]/).pop() || name;
    const i = base.lastIndexOf('.');
    return i > 0 ? base.slice(0, i) : base;
};

export function useCorporaImport() {
    const { t } = useI18n();
    const permiss = usePermissStore();
    const canImport = computed(() => permiss.hasApi('82', 'corpora-import'));

    const loading = ref(false);
    const categories = ref<Cat[]>([]);
    const fileList = ref<{ raw: File; name: string }[]>([]);
    const progressText = ref('');
    const lastResult = ref('');
    const nameFromFile = ref(false);
    let pollTimer: ReturnType<typeof setTimeout> | null = null;
    let pollStartedAt = 0;

    const form = reactive({
        corpus_name: '',
        category: 'other',
        replace_existing: true,
        chunk_strategy: 'structure',
        max_chunk_len: 500,
        min_chunk_len: 300,
        chunk_overlap: 80,
    });

    const errDetail = (err: unknown) =>
        err && typeof err === 'object' && 'response' in err
            ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
            : undefined;

    const clearPoll = () => {
        if (pollTimer) {
            clearTimeout(pollTimer);
            pollTimer = null;
        }
    };

    const loadCategories = async () => {
        try {
            const res = await listCorpusCategories();
            categories.value = (res.data as Cat[]) ?? [];
        } catch {
            categories.value = [];
        }
    };

    const onFileChange = (uploadFile: { raw?: File; name: string }) => {
        fileList.value = uploadFile.raw ? [{ raw: uploadFile.raw, name: uploadFile.name }] : [];
        if (uploadFile.raw) {
            const stem = fileStem(uploadFile.name);
            if (!form.corpus_name.trim() || nameFromFile.value) {
                form.corpus_name = stem;
                nameFromFile.value = true;
            }
        }
    };

    const onFileRemove = () => {
        fileList.value = [];
        if (nameFromFile.value) {
            form.corpus_name = '';
            nameFromFile.value = false;
        }
    };

    const onNameInput = () => {
        nameFromFile.value = false;
    };

    const pollJob = (jobId: string): Promise<JobStatus> =>
        new Promise((resolve, reject) => {
            const tick = async () => {
                if (Date.now() - pollStartedAt > TIMEOUT_MS) {
                    reject(new Error(t('pages.rag.corporaImportPanel.timeout')));
                    return;
                }
                try {
                    const res = await getCorpusImportJob(jobId);
                    const job = res.data as JobStatus;
                    progressText.value = t('pages.rag.corporaImportPanel.polling', {
                        status: job.status,
                        done: job.files_done ?? 0,
                        total: job.files_total ?? 0,
                        chunks: job.chunks ?? 0,
                    });
                    if (job.status === 'done' || job.status === 'failed') {
                        resolve(job);
                        return;
                    }
                    pollTimer = setTimeout(tick, POLL_MS);
                } catch (err) {
                    reject(err);
                }
            };
            void tick();
        });

    const submit = async () => {
        const file = fileList.value[0]?.raw ?? null;
        const name = form.corpus_name.trim();
        if (!file) {
            ElMessage.warning(t('pages.rag.corporaImportPanel.needSource'));
            return;
        }
        if (!name) {
            ElMessage.warning(t('pages.rag.corporaImportPanel.needName'));
            return;
        }
        loading.value = true;
        progressText.value = '';
        lastResult.value = '';
        clearPoll();
        try {
            const res = await importCorpus({
                file,
                corpus_name: name,
                category: form.category || 'other',
                replace_existing: form.replace_existing,
                chunk_strategy: form.chunk_strategy,
                max_chunk_len: form.max_chunk_len,
                min_chunk_len: form.min_chunk_len,
                chunk_overlap: form.chunk_overlap,
            });
            const jobId = (res.data as { job_id?: string })?.job_id;
            if (!jobId) throw new Error(t('pages.rag.corporaImportPanel.failed'));
            ElMessage.info(t('pages.rag.corporaImportPanel.accepted', { jobId }));
            pollStartedAt = Date.now();
            const final = await pollJob(jobId);
            lastResult.value = JSON.stringify(final, null, 2);
            if (final.status === 'done') {
                ElMessage.success(
                    t('pages.rag.corporaImportPanel.done', {
                        name: final.corpus_name || name,
                        files: final.files_total ?? 0,
                        chunks: final.chunks ?? 0,
                    }),
                );
            } else {
                ElMessage.error(final.error || t('pages.rag.corporaImportPanel.failed'));
            }
        } catch (err: unknown) {
            const msg =
                err instanceof Error
                    ? err.message
                    : errDetail(err) || t('pages.rag.corporaImportPanel.failed');
            ElMessage.error(String(msg));
            progressText.value = String(msg);
        } finally {
            clearPoll();
            loading.value = false;
        }
    };

    onMounted(() => {
        void loadCategories();
    });
    onUnmounted(clearPoll);

    return {
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
    };
}
