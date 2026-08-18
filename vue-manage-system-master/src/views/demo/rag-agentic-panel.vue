<template>
    <RagDemoShell
        title="多步 Agentic RAG"
        description="将复合问题拆成子问题，在业务库中多次检索后汇总。"
        :loading="loading"
        :answer="answer"
        @submit="run"
    >
        <template #fields>
            <el-form-item label="资料库" required>
                <el-select
                    v-model="corpusName"
                    filterable
                    clearable
                    :loading="corporaLoading"
                    placeholder="选择业务资料库"
                    style="width: 280px"
                >
                    <el-option v-for="c in corpora" :key="c.name" :label="c.name" :value="c.name" />
                </el-select>
            </el-form-item>
            <el-form-item label="问题" required>
                <el-input
                    v-model="question"
                    type="textarea"
                    :rows="3"
                    style="max-width: 560px"
                    placeholder="先查依赖注入怎么配，再说明中间件顺序注意点"
                />
            </el-form-item>
        </template>
        <template #extra>
            <el-timeline v-if="steps.length">
                <el-timeline-item v-for="(step, i) in steps" :key="i" :timestamp="`步骤 ${i + 1}`">
                    {{ step }}
                </el-timeline-item>
            </el-timeline>
        </template>
    </RagDemoShell>
</template>

<script setup lang="ts" name="rag-agentic-panel">
import { onMounted, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { listCorpora, ragAgentic } from '@/api';
import RagDemoShell from '@/views/demo/rag-demo-shell.vue';

const loading = ref(false);
const corporaLoading = ref(false);
const corpora = ref<{ name: string }[]>([]);
const corpusName = ref('');
const question = ref('先查高铁报销规则，如果涉及机票再补充舱位限制');
const answer = ref('');
const steps = ref<string[]>([]);

const loadCorpora = async () => {
    corporaLoading.value = true;
    try {
        const res = await listCorpora();
        corpora.value = (res.data as { name: string }[]) ?? [];
        if (!corpusName.value && corpora.value.length) {
            corpusName.value = corpora.value[0].name;
        }
    } catch {
        corpora.value = [];
    } finally {
        corporaLoading.value = false;
    }
};

const run = async () => {
    if (!corpusName.value.trim() || !question.value.trim()) {
        ElMessage.warning('请填写资料库与问题');
        return;
    }
    loading.value = true;
    answer.value = '';
    steps.value = [];
    try {
        const res = await ragAgentic({
            corpus_name: corpusName.value.trim(),
            question: question.value.trim(),
        });
        const data = res.data as { answer?: string; steps?: string[] };
        answer.value = data.answer ?? '';
        steps.value = data.steps ?? [];
    } catch (err: unknown) {
        const detail =
            err && typeof err === 'object' && 'response' in err
                ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
                : undefined;
        ElMessage.error(detail || 'Agentic 失败');
    } finally {
        loading.value = false;
    }
};

onMounted(loadCorpora);
</script>
