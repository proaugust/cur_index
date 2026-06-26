<template>
    <div class="container agent-page">
        <el-card shadow="hover">
            <template #header>
                <div class="page-header">
                    <div class="page-header-top">
                        <div>
                            <span class="page-title">Agent 架构展示</span>
                            <span class="page-subtitle">后端编排：原生 Python 与 LangChain 双引擎对比</span>
                        </div>
                        <el-radio-group v-model="activeEngine" size="small">
                            <el-radio-button value="native">原生 Agent</el-radio-button>
                            <el-radio-button value="langchain">LangChain Agent</el-radio-button>
                        </el-radio-group>
                    </div>
                </div>
            </template>

            <el-tabs v-model="activeTab" type="border-card">
                <el-tab-pane label="单智能体" name="single" lazy>
                    <ModeIntro
                        title="单智能体（Single Agent）"
                        desc="识别到算式时先走内置 calc 工具本地计算，再由 LLM 组织自然语言回答；普通问题则直接由 LLM 作答。"
                        :nodes="['用户', '工具 Agent', '回答 Agent', '答复']"
                    />
                    <AgentDemo
                        :loading="loading.single"
                        :steps="steps.single"
                        initial-question="123*456 等于多少"
                        placeholder="例如：123*456 等于多少（走计算器）或 什么是微服务（直接回答）"
                        hint="工作原理：含「等于多少」等词且能识别算式时，后端先用 calc 算出精确结果，再交给 LLM 生成答复；否则跳过工具，直接 LLM 回答。点下面示例可一键运行对比。"
                        empty-text="输入问题或点上方示例，查看 Agent 分步执行过程"
                        :examples="singleExamples"
                        @run="(q) => runAgent('single', q)"
                    />
                </el-tab-pane>

                <el-tab-pane label="顺序模式" name="sequential" lazy>
                    <ModeIntro
                        title="多智能体 · 顺序模式（Sequential）"
                        desc="多个 Agent 按固定流水线依次执行，前一步输出作为后一步输入，适合调研→撰写→润色等分阶段任务。"
                        :nodes="['用户', '规划 Agent', '执行 Agent', '总结 Agent', '回答']"
                    />
                    <AgentDemo
                        :loading="loading.sequential"
                        :steps="steps.sequential"
                        @run="(q) => runAgent('sequential', q)"
                    />
                </el-tab-pane>

                <el-tab-pane label="路由模式" name="routing" lazy>
                    <ModeIntro
                        title="多智能体 · 路由模式（Routing）"
                        desc="路由 Agent 先分析问题类型，再分发给对应专家 Agent，适合多领域混合问答场景。"
                        :nodes="['用户', '路由 Agent', '专家 Agent', '回答']"
                        :branches="['技术专家', '业务专家', '通用助手']"
                    />
                    <AgentDemo
                        :loading="loading.routing"
                        :steps="steps.routing"
                        @run="(q) => runAgent('routing', q)"
                    />
                </el-tab-pane>

                <el-tab-pane label="循环/反思模式" name="reflection" lazy>
                    <ModeIntro
                        title="多智能体 · 循环/反思模式（Loop / Reflection）"
                        desc="生成 Agent 产出草稿，评审 Agent 给出反馈并打分；未达标则迭代修订，适合对质量要求较高的输出。"
                        :nodes="['用户', '生成 Agent', '评审 Agent', '修订 Agent', '回答']"
                        :loop="true"
                    />
                    <AgentDemo
                        :loading="loading.reflection"
                        :steps="steps.reflection"
                        @run="(q) => runAgent('reflection', q)"
                    />
                </el-tab-pane>
            </el-tabs>
        </el-card>
    </div>
</template>

<script setup lang="ts" name="demo-agent">
import { defineAsyncComponent, reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { runAgent as runAgentApi } from '@/api';
import type { AgentExample, AgentStep } from './agent/types';

const ModeIntro = defineAsyncComponent(() => import('./agent/mode-intro.vue'));
const AgentDemo = defineAsyncComponent(() => import('./agent/agent-demo.vue'));
type AgentMode = 'single' | 'sequential' | 'routing' | 'reflection';
type AgentEngine = 'native' | 'langchain';

const activeTab = ref('single');
const activeEngine = ref<AgentEngine>('native');

const singleExamples: AgentExample[] = [
    {
        label: '计算器示例',
        question: '123*456 等于多少',
        tip: '识别算式 → 工具 Agent 本地计算 → 回答 Agent 转述结果',
    },
    {
        label: '直接问答',
        question: '用一句话解释什么是微服务',
        tip: '无算式 → 跳过工具，回答 Agent 直接调用 LLM',
    },
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
        ElMessage.warning('请输入问题');
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
        ElMessage.error('Agent 执行失败');
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
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
}

.page-header {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.page-title {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    display: block;
}

.page-subtitle {
    font-size: 13px;
    color: #909399;
    display: block;
    margin-top: 4px;
}
</style>
