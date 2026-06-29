<template>
    <div class="container ai-chat-page">
        <el-card shadow="hover" class="demo-card">
            <template #header>
                <div class="page-header">
                    <span class="page-title">{{ t('pages.aiChat.title') }}</span>
                    <FeatureIntroIcon
                        page-key="ai-chat"
                        section-key="page"
                        :intros="intros"
                        :title="t('pages.aiChat.title')"
                        @saved="setIntro"
                    />
                </div>
            </template>

            <div class="scenario-section">
                <div class="section-label">{{ t('pages.aiChat.scenarios') }}</div>
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
                    <el-collapse-item :title="t('pages.aiChat.params')" name="params">
                        <el-form label-width="100px" class="params-form">
                            <el-form-item :label="t('pages.aiChat.systemPrompt')">
                                <el-input
                                    v-model="systemPrompt"
                                    type="textarea"
                                    :rows="2"
                                    :placeholder="t('pages.aiChat.systemPromptPh')"
                                    :disabled="loading"
                                />
                            </el-form-item>
                            <el-form-item :label="t('pages.aiChat.temperature')">
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
                                <div class="temp-hint">{{ t('pages.aiChat.tempHint') }}</div>
                            </el-form-item>
                        </el-form>
                    </el-collapse-item>
                </el-collapse>
            </div>

            <div class="chat-section">
                <div class="section-label">{{ t('pages.aiChat.chatLog') }}</div>
                <div ref="chatBoxRef" class="chat-box">
                    <div
                        v-for="(msg, idx) in displayMessages"
                        :key="idx"
                        class="chat-row"
                        :class="msg.role"
                    >
                        <div class="chat-bubble">
                            <span class="chat-role">{{ msg.role === 'user' ? t('pages.aiChat.roleUser') : t('pages.aiChat.roleAssistant') }}</span>
                            <div class="chat-content">{{ msg.content }}</div>
                        </div>
                    </div>
                    <el-empty v-if="!displayMessages.length" :description="t('pages.aiChat.chatEmpty')" :image-size="64" />
                </div>
            </div>

            <div class="input-section">
                <div class="section-label">{{ t('pages.aiChat.inputQuestion') }}</div>
                <el-input
                    v-model="question"
                    type="textarea"
                    :rows="3"
                    :placeholder="t('pages.aiChat.inputPh')"
                    :disabled="loading"
                    @keydown.ctrl.enter="handleSend"
                />
                <div class="action-bar">
                    <el-button type="primary" :loading="loading" :disabled="!question.trim()" @click="handleSend">
                        {{ t('common.send') }}
                    </el-button>
                    <el-button :disabled="loading" @click="handleClear">{{ t('pages.aiChat.clearChat') }}</el-button>
                </div>
            </div>
        </el-card>

        <LazyApiDebugPanel endpoint-key="chat" class="debug-panel" />
    </div>
</template>

<script setup lang="ts" name="demo-ai-chat">
import { computed, nextTick, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import LazyApiDebugPanel from '@/components/lazy-api-debug-panel.vue';
import FeatureIntroIcon from '@/components/feature-intro-icon.vue';
import { useFeatureIntros } from '@/composables/useFeatureIntros';
import { hasDemoCache, useCachedRef } from '@/composables/useFormCache';
import { askChat } from '@/api';

const { t, locale } = useI18n();
const { intros, setIntro } = useFeatureIntros('ai-chat');

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

const scenarios = computed<Scenario[]>(() => [
    {
        id: 'direct',
        label: t('pages.aiChat.scenarioDirect'),
        tag: t('pages.aiChat.tagSingle'),
        tagType: 'success',
        hint: t('pages.aiChat.hintDirect'),
        question: t('pages.aiChat.qDirect'),
        system_prompt: '',
        history: [],
        temperature: 0.7,
    },
    {
        id: 'persona',
        label: t('pages.aiChat.scenarioPersona'),
        tag: t('pages.aiChat.tagSystemPrompt'),
        tagType: 'warning',
        hint: t('pages.aiChat.hintPersona'),
        question: t('pages.aiChat.qPersona'),
        system_prompt: t('pages.aiChat.personaSystem'),
        history: [],
        temperature: 0.7,
    },
    {
        id: 'multi',
        label: t('pages.aiChat.scenarioMulti'),
        tag: t('pages.aiChat.tagHistory'),
        tagType: 'info',
        hint: t('pages.aiChat.hintMulti'),
        question: t('pages.aiChat.qMulti'),
        system_prompt: '',
        history: [
            { role: 'user', content: t('pages.aiChat.historyUser') },
            { role: 'assistant', content: t('pages.aiChat.historyAssistant') },
        ],
        temperature: 0.7,
    },
    {
        id: 'random-low',
        label: t('pages.aiChat.scenarioRandomLow'),
        tag: t('pages.aiChat.tagTempLow'),
        tagType: '',
        hint: t('pages.aiChat.hintRandomLow'),
        question: t('pages.aiChat.qRandom'),
        system_prompt: '',
        history: [],
        temperature: 0.1,
    },
    {
        id: 'random-high',
        label: t('pages.aiChat.scenarioRandomHigh'),
        tag: t('pages.aiChat.tagTempHigh'),
        tagType: 'danger',
        hint: t('pages.aiChat.hintRandomHigh'),
        question: t('pages.aiChat.qRandom'),
        system_prompt: '',
        history: [],
        temperature: 1.5,
    },
]);

const question = useCachedRef('ai-chat:question', '');
const systemPrompt = useCachedRef('ai-chat:systemPrompt', '');
const temperature = useCachedRef('ai-chat:temperature', 0.7);
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

watch(
    scenarios,
    (list) => {
        if (!list.length) return;
        const hasSavedInput =
            hasDemoCache('ai-chat:question') ||
            hasDemoCache('ai-chat:systemPrompt') ||
            hasDemoCache('ai-chat:temperature');
        if (!hasSavedInput) {
            applyScenario(list[0]);
        }
    },
    { immediate: true },
);

watch(locale, () => {
    const current = scenarios.value.find((item) => item.id === activeScenario.value) ?? scenarios.value[0];
    if (current) {
        applyScenario(current);
    }
});

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
        ElMessage.error(typeof msg === 'string' ? msg : t('pages.aiChat.askFailed'));
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
</script>

<style scoped>
.ai-chat-page {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.demo-card .page-header {
    display: inline-flex;
    align-items: center;
    gap: 0;
}

.demo-card .page-title {
    font-size: 16px;
    font-weight: 600;
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
