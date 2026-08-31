<template>
    <div class="container agent-page">
        <el-card shadow="hover">
            <template #header>
                <div class="page-header">
                    <div class="page-header-top">
                        <span class="page-title">{{ title }}</span>
                    </div>
                </div>
            </template>

            <el-tabs v-model="activeTab" type="border-card">
                <el-tab-pane name="single" lazy>
                    <template #label>
                        <span class="tab-label-with-intro">
                            {{ t('pages.agent.tabSingle') }}
                            <FeatureIntroIcon
                                page-key="agent"
                                section-key="single"
                                :intros="intros"
                                :title="t('pages.agent.tabSingle')"
                                @saved="setIntro"
                            />
                        </span>
                    </template>
                    <ModeIntro
                        :title="t('pages.agent.modeSingleTitle')"
                        :nodes="[t('pages.agent.nodeUser'), '工具 Agent', '回答 Agent', t('pages.agent.nodeReply')]"
                    />
                    <AgentDemo
                        :cache-key="`${engine}-single`"
                        :loading="loading.single"
                        :steps="steps.single"
                        :initial-question="singleExamples[0].question"
                        :placeholder="t('pages.agent.singlePlaceholder')"
                        :hint="t('pages.agent.singleHint')"
                        :empty-text="t('pages.agent.singleEmpty')"
                        :examples="singleExamples"
                        @run="(q) => runAgent('single', q)"
                    />
                </el-tab-pane>

                <el-tab-pane name="sequential" lazy>
                    <template #label>
                        <span class="tab-label-with-intro">
                            {{ t('pages.agent.tabSequential') }}
                            <FeatureIntroIcon
                                page-key="agent"
                                section-key="sequential"
                                :intros="intros"
                                :title="t('pages.agent.tabSequential')"
                                @saved="setIntro"
                            />
                        </span>
                    </template>
                    <ModeIntro
                        :title="t('pages.agent.modeSequentialTitle')"
                        :nodes="[t('pages.agent.nodeUser'), '规划 Agent', '执行 Agent', '总结 Agent', t('pages.agent.nodeAnswer')]"
                    />
                    <AgentDemo
                        :cache-key="`${engine}-sequential`"
                        :loading="loading.sequential"
                        :steps="steps.sequential"
                        :initial-question="defaultQuestions.sequential"
                        @run="(q) => runAgent('sequential', q)"
                    />
                </el-tab-pane>

                <el-tab-pane name="routing" lazy>
                    <template #label>
                        <span class="tab-label-with-intro">
                            {{ t('pages.agent.tabRouting') }}
                            <FeatureIntroIcon
                                page-key="agent"
                                section-key="routing"
                                :intros="intros"
                                :title="t('pages.agent.tabRouting')"
                                @saved="setIntro"
                            />
                        </span>
                    </template>
                    <ModeIntro
                        :title="t('pages.agent.modeRoutingTitle')"
                        :nodes="[t('pages.agent.nodeUser'), '路由 Agent', '专家 Agent', t('pages.agent.nodeAnswer')]"
                        :branches="[t('pages.agent.branchTech'), t('pages.agent.branchBiz'), t('pages.agent.branchGeneral')]"
                    />
                    <AgentDemo
                        :cache-key="`${engine}-routing`"
                        :loading="loading.routing"
                        :steps="steps.routing"
                        :initial-question="defaultQuestions.routing"
                        @run="(q) => runAgent('routing', q)"
                    />
                </el-tab-pane>

                <el-tab-pane name="reflection" lazy>
                    <template #label>
                        <span class="tab-label-with-intro">
                            {{ t('pages.agent.tabReflection') }}
                            <FeatureIntroIcon
                                page-key="agent"
                                section-key="reflection"
                                :intros="intros"
                                :title="t('pages.agent.tabReflection')"
                                @saved="setIntro"
                            />
                        </span>
                    </template>
                    <ModeIntro
                        :title="t('pages.agent.modeReflectionTitle')"
                        :nodes="[t('pages.agent.nodeUser'), '生成 Agent', '评审 Agent', '修订 Agent', t('pages.agent.nodeAnswer')]"
                        :loop="true"
                    />
                    <AgentDemo
                        :cache-key="`${engine}-reflection`"
                        :loading="loading.reflection"
                        :steps="steps.reflection"
                        :initial-question="defaultQuestions.reflection"
                        :lanes="reflectionLanes"
                        @run="(q) => runAgent('reflection', q)"
                    />
                </el-tab-pane>
            </el-tabs>
        </el-card>
    </div>
</template>

<script setup lang="ts" name="agent-panel">
import { computed, defineAsyncComponent, reactive } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import FeatureIntroIcon from '@/components/feature-intro-icon.vue';
import { useFeatureIntros } from '@/composables/useFeatureIntros';
import { useCachedRef } from '@/composables/useFormCache';
import { runNativeAgent, runNativeAgentStream } from '@/api';
import type { AgentExample, AgentLane, AgentStep } from './types';

const ModeIntro = defineAsyncComponent(() => import('./mode-intro.vue'));
const AgentDemo = defineAsyncComponent(() => import('./agent-demo.vue'));
type AgentMode = 'single' | 'sequential' | 'routing' | 'reflection';

const props = defineProps<{
    engine: 'native';
    title: string;
}>();

const { t } = useI18n();
const { intros, setIntro } = useFeatureIntros('agent');

const activeTab = useCachedRef(`agent:${props.engine}:activeTab`, 'single');

const singleExamples = computed<AgentExample[]>(() => [
    {
        label: t('pages.agent.calcExample'),
        question: t('pages.agent.calcQuestion'),
        tip: t('pages.agent.calcTip'),
    },
    {
        label: t('pages.agent.directQa'),
        question: t('pages.agent.directQuestion'),
        tip: t('pages.agent.directTip'),
    },
]);

const defaultQuestions = computed(() => ({
    sequential: t('pages.agent.sequentialQuestion'),
    routing: t('pages.agent.routingQuestion'),
    reflection: t('pages.agent.reflectionQuestion'),
}));

const reflectionLanes: AgentLane[] = [
    { agent: '生成 Agent', title: '生成' },
    { agent: '评审 Agent', title: '评审' },
    { agent: '修订 Agent', title: '修订' },
    { agent: '最终输出', title: '最终' },
];

const seedReflectionSteps = (question: string): AgentStep[] => [
    { agent: '生成 Agent', role: '第 1 轮初稿', input: question, output: '', status: 'running' },
    { agent: '评审 Agent', role: '等待评审', input: '', output: '', status: 'pending' },
    { agent: '修订 Agent', role: '等待修订', input: '', output: '', status: 'pending' },
    { agent: '最终输出', role: '等待终稿', input: '', output: '', status: 'pending' },
];

const loading = reactive({
    single: false,
    sequential: false,
    routing: false,
    reflection: false,
});

const steps = reactive<Record<AgentMode, AgentStep[]>>({
    single: [],
    sequential: [],
    routing: [],
    reflection: [],
});

const runAgent = async (mode: AgentMode, question: string) => {
    if (!question.trim()) {
        ElMessage.warning(t('pages.agent.enterQuestion'));
        return;
    }
    loading[mode] = true;
    if (mode === 'reflection') {
        steps.reflection = seedReflectionSteps(question);
    } else {
        steps[mode] = [];
    }
    try {
        if (mode === 'reflection') {
            await runNativeAgentStream({ question, mode, temperature: 0.7 }, (payload) => {
                steps.reflection = payload.steps.map((step) => ({
                    ...step,
                    meta: step.meta ?? undefined,
                }));
            });
        } else {
            const res = await runNativeAgent({
                question,
                mode,
                temperature: 0.7,
            });
            steps[mode] = res.data.steps ?? [];
        }
    } catch {
        ElMessage.error(t('pages.agent.runFailed'));
    } finally {
        loading[mode] = false;
    }
};
</script>

<style scoped>
.agent-page {
    min-height: calc(100vh - 140px);
}

.page-header-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
}

.page-title {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
}

.tab-label-with-intro {
    display: inline-flex;
    align-items: center;
}
</style>
