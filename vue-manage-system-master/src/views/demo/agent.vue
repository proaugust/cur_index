<template>
    <div class="container agent-page">
        <el-card shadow="hover">
            <template #header>
                <div class="page-header">
                    <div class="page-header-top">
                        <span class="page-title">{{ t('pages.agent.title') }}</span>
                        <el-radio-group v-model="activeEngine" size="small">
                            <el-radio-button value="native">{{ t('pages.agent.nativeAgent') }}</el-radio-button>
                            <el-radio-button value="langchain">{{ t('pages.agent.langchainAgent') }}</el-radio-button>
                        </el-radio-group>
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
                        cache-key="single"
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
                        cache-key="sequential"
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
                        cache-key="routing"
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
                        cache-key="reflection"
                        :loading="loading.reflection"
                        :steps="steps.reflection"
                        :initial-question="defaultQuestions.reflection"
                        @run="(q) => runAgent('reflection', q)"
                    />
                </el-tab-pane>
            </el-tabs>
        </el-card>
    </div>
</template>

<script setup lang="ts" name="demo-agent">
import { computed, defineAsyncComponent, reactive } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import FeatureIntroIcon from '@/components/feature-intro-icon.vue';
import { useFeatureIntros } from '@/composables/useFeatureIntros';
import { useCachedRef } from '@/composables/useFormCache';
import { runAgent as runAgentApi } from '@/api';
import type { AgentExample, AgentStep } from './agent/types';

const ModeIntro = defineAsyncComponent(() => import('./agent/mode-intro.vue'));
const AgentDemo = defineAsyncComponent(() => import('./agent/agent-demo.vue'));
type AgentMode = 'single' | 'sequential' | 'routing' | 'reflection';
type AgentEngine = 'native' | 'langchain';

const { t, locale } = useI18n();
const { intros, setIntro } = useFeatureIntros('agent');

void locale;

const activeTab = useCachedRef('agent:activeTab', 'single');
const activeEngine = useCachedRef<AgentEngine>('agent:activeEngine', 'native');

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
    steps[mode] = [];
    try {
        const res = await runAgentApi({
            question,
            mode,
            engine: activeEngine.value,
            temperature: 0.7,
        });
        steps[mode] = res.data.steps ?? [];
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
