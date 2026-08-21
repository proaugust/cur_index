<template>
    <div class="container agent-page">
        <el-card shadow="hover">
            <template #header>
                <span class="page-title">{{ t('pages.agent.langchainSection') }}</span>
            </template>
            <ModeIntro
                :title="t('pages.agent.langchainExampleTitle')"
                :nodes="[
                    t('pages.agent.nodeUser'),
                    t('pages.agent.langchainNodeFanout'),
                    t('pages.agent.langchainNodeMerge'),
                    t('pages.agent.nodeReply'),
                ]"
            />
            <AgentDemo
                cache-key="langchain-graph"
                :loading="loading"
                :steps="steps"
                :initial-question="t('pages.agent.langchainQuestion')"
                :hint="t('pages.agent.langchainHint')"
                :examples="examples"
                @run="run"
            />
        </el-card>
    </div>
</template>

<script setup lang="ts" name="demo-agent-langchain">
import { computed, defineAsyncComponent, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import { runLangchainAgent } from '@/api';
import type { AgentExample, AgentStep } from './types';

const ModeIntro = defineAsyncComponent(() => import('./mode-intro.vue'));
const AgentDemo = defineAsyncComponent(() => import('./agent-demo.vue'));

const { t } = useI18n();
const loading = ref(false);
const steps = ref<AgentStep[]>([]);
const examples = computed<AgentExample[]>(() => [
    {
        label: t('pages.agent.langchainExample'),
        question: t('pages.agent.langchainQuestion'),
        tip: t('pages.agent.langchainTip'),
    },
]);

const run = async (question: string) => {
    if (!question.trim()) {
        ElMessage.warning(t('pages.agent.enterQuestion'));
        return;
    }
    loading.value = true;
    steps.value = [];
    try {
        const res = await runLangchainAgent({
            question,
            temperature: 0.7,
        });
        steps.value = res.data.steps ?? [];
    } catch {
        ElMessage.error(t('pages.agent.runFailed'));
    } finally {
        loading.value = false;
    }
};
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
</style>
