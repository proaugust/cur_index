<template>
    <div class="container agent-page">
        <el-card shadow="hover">
            <template #header>
                <span class="page-title">{{ t('pages.agent.crewaiSection') }}</span>
            </template>
            <ModeIntro
                :title="t('pages.agent.crewaiExampleTitle')"
                :nodes="[
                    t('pages.agent.nodeUser'),
                    t('pages.agent.crewaiResearcher'),
                    t('pages.agent.crewaiWriter'),
                    t('pages.agent.nodeReply'),
                ]"
            />
            <AgentDemo
                cache-key="crewai-simple"
                :loading="loading"
                :steps="steps"
                :initial-question="t('pages.agent.crewaiQuestion')"
                :hint="t('pages.agent.crewaiHint')"
                :examples="examples"
                @run="run"
            />
        </el-card>
    </div>
</template>

<script setup lang="ts" name="demo-agent-crewai">
import { computed, defineAsyncComponent, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import { runCrewaiAgent } from '@/api';
import type { AgentExample, AgentStep } from './types';

const ModeIntro = defineAsyncComponent(() => import('./mode-intro.vue'));
const AgentDemo = defineAsyncComponent(() => import('./agent-demo.vue'));

const { t } = useI18n();
const loading = ref(false);
const steps = ref<AgentStep[]>([]);
const examples = computed<AgentExample[]>(() => [
    {
        label: t('pages.agent.crewaiExample'),
        question: t('pages.agent.crewaiQuestion'),
        tip: t('pages.agent.crewaiTip'),
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
        const res = await runCrewaiAgent({
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
