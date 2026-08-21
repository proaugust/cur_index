<template>
    <div class="container agent-page">
        <el-card shadow="hover">
            <template #header>
                <span class="page-title">{{ t('pages.agent.agenticSection') }}</span>
            </template>
            <ModeIntro
                :title="t('pages.agent.agenticExampleTitle')"
                :nodes="[
                    t('pages.agent.nodeUser'),
                    t('pages.agent.agenticPlan'),
                    t('pages.agent.agenticRetrieve'),
                    t('pages.agent.agenticSummarize'),
                    t('pages.agent.nodeReply'),
                ]"
            />
            <div class="corpus-row">
                <span class="corpus-label">{{ t('pages.agent.corpusLabel') }}</span>
                <el-select
                    v-model="corpusName"
                    filterable
                    clearable
                    :loading="corporaLoading"
                    :placeholder="t('pages.agent.selectCorpus')"
                    style="width: 280px"
                >
                    <el-option v-for="c in corpora" :key="c.name" :label="c.name" :value="c.name" />
                </el-select>
            </div>
            <AgentDemo
                cache-key="agentic-rag"
                :loading="loading"
                :steps="steps"
                :initial-question="t('pages.agent.agenticQuestion')"
                :hint="t('pages.agent.agenticHint')"
                :examples="examples"
                @run="run"
            />
        </el-card>
    </div>
</template>

<script setup lang="ts" name="demo-agent-agentic">
import { computed, defineAsyncComponent, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import { listCorpora, runAgenticAgent } from '@/api';
import type { AgentExample, AgentStep } from './types';

const ModeIntro = defineAsyncComponent(() => import('./mode-intro.vue'));
const AgentDemo = defineAsyncComponent(() => import('./agent-demo.vue'));

const { t } = useI18n();
const loading = ref(false);
const corporaLoading = ref(false);
const corpora = ref<{ name: string }[]>([]);
const corpusName = ref('');
const steps = ref<AgentStep[]>([]);
const examples = computed<AgentExample[]>(() => [
    {
        label: t('pages.agent.agenticExample'),
        question: t('pages.agent.agenticQuestion'),
        tip: t('pages.agent.agenticTip'),
    },
]);

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

const run = async (question: string) => {
    if (!corpusName.value.trim() || !question.trim()) {
        ElMessage.warning(t('pages.agent.enterCorpus'));
        return;
    }
    loading.value = true;
    steps.value = [];
    try {
        const res = await runAgenticAgent({
            corpus_name: corpusName.value.trim(),
            question: question.trim(),
        });
        steps.value = res.data.steps ?? [];
    } catch {
        ElMessage.error(t('pages.agent.runFailed'));
    } finally {
        loading.value = false;
    }
};

onMounted(loadCorpora);
</script>

<style scoped>
.agent-page {
    min-height: calc(100vh - 140px);
}
.page-title {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
}
.corpus-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
}
.corpus-label {
    font-size: 13px;
    color: #606266;
    white-space: nowrap;
}
</style>
