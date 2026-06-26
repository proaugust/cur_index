<template>
    <div class="container ai-chat-page">
        <el-card shadow="hover" class="demo-card">
            <template #header>
                <div class="page-header">
                    <span class="page-title">AI 训练提问</span>
                    <span class="page-subtitle">点击示例体验四种 LLM 调用方式，下方可继续调试原始接口</span>
                </div>
            </template>

            <div class="scenario-section">
                <div class="section-label">示例场景（点一下即发送）</div>
                <div class="scenario-buttons">
                    <el-button
                        v-for="item in scenarios"
                        :key="item.id"
                        :type="activeScenario === item.id ? 'primary' : 'default'"
                        :disabled="loading"
                        @click="handleScenario(item)"
                    >
                        <span class="scenario-label">{{ item.label }}</span>
                        <el-tag size="small" :type="item.tagType" class="scenario-tag">{{ item.tag }}</el-tag>
                    </el-button>
                </div>
                <p v-if="activeHint" class="scenario-hint">{{ activeHint }}</p>
            </div>

            <div class="params-section">
                <el-collapse v-model="paramsExpanded">
                    <el-collapse-item title="当前调用参数（随场景变化）" name="params">
                        <el-form label-width="100px" class="params-form">
                            <el-form-item label="系统提示词">
                                <el-input
                                    v-model="systemPrompt"
                                    type="textarea"
                                    :rows="2"
                                    placeholder="留空使用后端默认提示词"
                                    :disabled="loading"
                                />
                            </el-form-item>
                            <el-form-item label="温度">
                                <div class="temp-row">
                                    <el-slider
                                        v-model="temperature"
                                        :min="0"
                                        :max="2"
                                        :step="0.1"
                                        :disabled="loading"
                                        class="temp-slider"
                                    />
                                    <span class="temp-value">{{ temperature.toFixed(1) }}</span>
                                </div>
                                <div class="temp-hint">越低越稳定，越高越发散</div>
                            </el-form-item>
                        </el-form>
                    </el-collapse-item>
                </el-collapse>
            </div>

            <div class="chat-section">
                <div class="section-label">对话记录</div>
                <div ref="chatBoxRef" class="chat-box">
                    <div
                        v-for="(msg, idx) in displayMessages"
                        :key="idx"
                        class="chat-row"
                        :class="msg.role"
                    >
                        <div class="chat-bubble">
                            <span class="chat-role">{{ msg.role === 'user' ? '用户' : '助手' }}</span>
                            <div class="chat-content">{{ msg.content }}</div>
                        </div>
                    </div>
                    <el-empty v-if="!displayMessages.length" description="选择上方示例或自行输入问题" :image-size="64" />
                </div>
            </div>

            <div class="input-section">
                <div class="section-label">输入问题</div>
                <el-input
                    v-model="question"
                    type="textarea"
                    :rows="3"
                    placeholder="输入你的问题，或点击上方示例自动填入并发送"
                    :disabled="loading"
                    @keydown.ctrl.enter="handleSend"
                />
                <div class="action-bar">
                    <el-button type="primary" :loading="loading" :disabled="!question.trim()" @click="handleSend">
                        发送
                    </el-button>
                    <el-button :disabled="loading" @click="handleClear">清空对话</el-button>
                </div>
            </div>
        </el-card>

        <LazyApiDebugPanel endpoint-key="chat" class="debug-panel" />
    </div>
</template>

<script setup lang="ts" name="demo-ai-chat">
import { nextTick, ref } from 'vue';
import { ElMessage } from 'element-plus';
import LazyApiDebugPanel from '@/components/lazy-api-debug-panel.vue';
import { askChat } from '@/api';

type ChatRole = 'user' | 'assistant';
type ChatMessage = { role: ChatRole; content: string };

interface Scenario {
    id: string;
    label: string;
    tag: string;
    tagType: '' | 'success' | 'warning' | 'info' | 'danger';
    hint: string;
    question: string;
    system_prompt: string;
    history: ChatMessage[];
    temperature: number;
}

const scenarios: Scenario[] = [
    {
        id: 'direct',
        label: '直接问 LLM',
        tag: '单轮',
        tagType: 'success',
        hint: '默认系统提示词 + 空历史，最基础的单次问答。',
        question: '用一句话解释什么是大语言模型。',
        system_prompt: '',
        history: [],
        temperature: 0.7,
    },
    {
        id: 'persona',
        label: '定制人设',
        tag: 'system_prompt',
        tagType: 'warning',
        hint: '通过 system_prompt 训练回答风格——同一问题，人设不同，回答完全不同。',
        question: '请介绍一下你自己。',
        system_prompt: '你是一位江湖侠客，说话带古风，每句末尾加「是也」或「耳」，绝不使用现代网络用语。',
        history: [],
        temperature: 0.7,
    },
    {
        id: 'multi',
        label: '多轮对话',
        tag: 'history',
        tagType: 'info',
        hint: '请求会带上 history，模型能记住前文——试试问「我刚才说我叫什么」。',
        question: '我刚才说我叫什么名字？在哪个城市工作？',
        system_prompt: '',
        history: [
            { role: 'user', content: '我叫小明，在成都做后端开发。' },
            { role: 'assistant', content: '你好小明！成都是一座很棒的城市。后端开发有什么我可以帮你的吗？' },
        ],
        temperature: 0.7,
    },
    {
        id: 'random-low',
        label: '随机性 · 低',
        tag: 'temp≈0.1',
        tagType: '',
        hint: '低温度：同一问题每次回答更稳定、更接近。',
        question: '给一家奶茶店起 3 个有创意的名字。',
        system_prompt: '',
        history: [],
        temperature: 0.1,
    },
    {
        id: 'random-high',
        label: '随机性 · 高',
        tag: 'temp≈1.5',
        tagType: 'danger',
        hint: '高温度：同一问题回答更发散、更有意外感——可与「随机性·低」对比。',
        question: '给一家奶茶店起 3 个有创意的名字。',
        system_prompt: '',
        history: [],
        temperature: 1.5,
    },
];

const question = ref(scenarios[0].question);
const systemPrompt = ref('');
const temperature = ref(0.7);
const history = ref<ChatMessage[]>([]);
const displayMessages = ref<ChatMessage[]>([]);
const loading = ref(false);
const activeScenario = ref('');
const activeHint = ref('');
const paramsExpanded = ref(['params']);
const chatBoxRef = ref<HTMLElement | null>(null);

const scrollToBottom = async () => {
    await nextTick();
    const el = chatBoxRef.value;
    if (el) el.scrollTop = el.scrollHeight;
};

const applyScenario = (item: Scenario) => {
    activeScenario.value = item.id;
    activeHint.value = item.hint;
    question.value = item.question;
    systemPrompt.value = item.system_prompt;
    temperature.value = item.temperature;
    history.value = [...item.history];
    displayMessages.value = [...item.history];
};

const handleScenario = async (item: Scenario) => {
    applyScenario(item);
    await handleSend();
};

const handleSend = async () => {
    const q = question.value.trim();
    if (!q || loading.value) return;

    loading.value = true;
    const userMsg: ChatMessage = { role: 'user', content: q };
    displayMessages.value.push(userMsg);

    try {
        const res = await askChat({
            question: q,
            system_prompt: systemPrompt.value.trim() || undefined,
            history: history.value,
            temperature: temperature.value,
        });
        const answer = res.data.answer;
        const assistantMsg: ChatMessage = { role: 'assistant', content: answer };
        displayMessages.value.push(assistantMsg);
        history.value = [...history.value, userMsg, assistantMsg];
        question.value = '';
        await scrollToBottom();
    } catch (err: unknown) {
        displayMessages.value.pop();
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        ElMessage.error(typeof msg === 'string' ? msg : '提问失败，请稍后重试');
    } finally {
        loading.value = false;
    }
};

const handleClear = () => {
    question.value = '';
    systemPrompt.value = '';
    temperature.value = 0.7;
    history.value = [];
    displayMessages.value = [];
    activeScenario.value = '';
    activeHint.value = '';
};

applyScenario(scenarios[0]);
</script>

<style scoped>
.ai-chat-page {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.demo-card .page-header {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.demo-card .page-title {
    font-size: 16px;
    font-weight: 600;
}

.demo-card .page-subtitle {
    font-size: 13px;
    color: var(--el-text-color-secondary);
}

.section-label {
    margin-bottom: 8px;
    font-size: 14px;
    font-weight: 500;
}

.scenario-buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.scenario-label {
    margin-right: 6px;
}

.scenario-tag {
    vertical-align: middle;
}

.scenario-hint {
    margin: 10px 0 0;
    font-size: 13px;
    color: var(--el-text-color-secondary);
    line-height: 1.5;
}

.params-section {
    margin-top: 16px;
}

.params-form {
    padding-top: 4px;
}

.temp-row {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
}

.temp-slider {
    flex: 1;
}

.temp-value {
    min-width: 28px;
    font-variant-numeric: tabular-nums;
    color: var(--el-text-color-secondary);
}

.temp-hint {
    margin-top: 4px;
    font-size: 12px;
    color: var(--el-text-color-placeholder);
}

.chat-section {
    margin-top: 16px;
}

.chat-box {
    min-height: 220px;
    max-height: 360px;
    overflow-y: auto;
    padding: 12px;
    border: 1px solid var(--el-border-color-light);
    border-radius: 4px;
    background: var(--el-fill-color-lighter);
}

.chat-row {
    display: flex;
    margin-bottom: 12px;
}

.chat-row.user {
    justify-content: flex-end;
}

.chat-row.assistant {
    justify-content: flex-start;
}

.chat-bubble {
    max-width: 85%;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 14px;
    line-height: 1.6;
}

.chat-row.user .chat-bubble {
    background: var(--el-color-primary-light-9);
    border: 1px solid var(--el-color-primary-light-7);
}

.chat-row.assistant .chat-bubble {
    background: var(--el-fill-color-blank);
    border: 1px solid var(--el-border-color-light);
}

.chat-role {
    display: block;
    margin-bottom: 4px;
    font-size: 12px;
    font-weight: 600;
    color: var(--el-text-color-secondary);
}

.chat-content {
    white-space: pre-wrap;
    word-break: break-word;
}

.input-section {
    margin-top: 16px;
}

.action-bar {
    margin-top: 12px;
    display: flex;
    gap: 8px;
}

.debug-panel {
    margin-bottom: 0;
}
</style>
