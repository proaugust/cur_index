<template>
    <div class="container agent-page">
        <el-card shadow="hover">
            <template #header>
                <span class="page-title">{{ t('pages.agent.autogenSection') }}</span>
            </template>
            <ModeIntro
                :title="t('pages.agent.autogenExampleTitle')"
                :nodes="[
                    t('pages.agent.nodeUser'),
                    'Assistant',
                    'Critic',
                    'Assistant',
                    t('pages.agent.nodeReply'),
                ]"
                :loop="true"
            />
            <AgentDemo
                cache-key="autogen-simple"
                :loading="loading"
                :steps="steps"
                :initial-question="t('pages.agent.autogenQuestion')"
                :hint="t('pages.agent.autogenHint')"
                :examples="examples"
                @run="run"
            />
        </el-card>
    </div>
</template>

<script setup lang="ts" name="demo-agent-autogen">
import { computed, defineAsyncComponent, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import { runAutogenAgent } from '@/api';
import type { AgentExample, AgentStep } from './types';

const ModeIntro = defineAsyncComponent(() => import('./mode-intro.vue'));
const AgentDemo = defineAsyncComponent(() => import('./agent-demo.vue'));

const { t } = useI18n();
const loading = ref(false);
const steps = ref<AgentStep[]>([]);
const examples = computed<AgentExample[]>(() => [
    {
        label: t('pages.agent.autogenExample'),
        question: t('pages.agent.autogenQuestion'),
        tip: t('pages.agent.autogenTip'),
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
        const res = await runAutogenAgent({
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
