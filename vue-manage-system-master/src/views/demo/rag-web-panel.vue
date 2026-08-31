<template>
    <RagDemoShell
        title="时效 Web 检索"
        description="优先 Bing Web Search；未配置 BING_SEARCH_API_KEY 时自动用样例网页演示。"
        :loading="loading"
        :answer="answer"
        @submit="run"
    >
        <template #fields>
            <el-form-item label="问题" required>
                <el-input
                    v-model="question"
                    clearable
                    style="max-width: 560px"
                    placeholder="今天 AI 行业有哪些最新动态？"
                />
            </el-form-item>
        </template>
        <template #extra>
            <el-alert
                v-if="searchMode === 'sample'"
                type="info"
                :closable="false"
                show-icon
                title="未配置 Bing Key，当前为样例网页模式（标题不可点，不是真实网站）"
                style="margin-bottom: 12px"
            />
            <div v-for="(s, i) in sources" :key="i" class="answer-box">
                <div class="answer-label">
                    <a
                        v-if="searchMode !== 'sample' && isExternalUrl(s.url)"
                        :href="s.url"
                        target="_blank"
                        rel="noopener"
                    >{{ s.title || s.url }}</a>
                    <span v-else>{{ s.title || s.url }}</span>
                </div>
                <div class="answer-body">{{ s.snippet }}</div>
            </div>
        </template>
    </RagDemoShell>
</template>

<script setup lang="ts" name="rag-web-panel">
import { ref } from 'vue';
import { ElMessage } from 'element-plus';
import { ragWebSearch } from '@/api';
import RagDemoShell from '@/views/demo/rag-demo-shell.vue';

const loading = ref(false);
const question = ref('今天人工智能有哪些最新新闻？');
const answer = ref('');
const searchMode = ref('');
const sources = ref<{ title: string; url: string; snippet: string }[]>([]);

const isExternalUrl = (url?: string) => {
    if (!url) return false;
    try {
        const host = new URL(url).hostname;
        return host !== 'example.com' && !host.endsWith('.example.com');
    } catch {
        return false;
    }
};

const run = async () => {
    if (!question.value.trim()) {
        ElMessage.warning('请输入问题');
        return;
    }
    loading.value = true;
    answer.value = '';
    searchMode.value = '';
    sources.value = [];
    try {
        const res = await ragWebSearch({ question: question.value.trim() });
        const data = res.data as {
            answer?: string;
            search_mode?: string;
            sources?: { title: string; url: string; snippet: string }[];
        };
        answer.value = data.answer ?? '';
        searchMode.value = data.search_mode ?? '';
        sources.value = data.sources ?? [];
    } catch (err: unknown) {
        const detail =
            err && typeof err === 'object' && 'response' in err
                ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
                : undefined;
        ElMessage.error(detail || 'Web 检索失败');
    } finally {
        loading.value = false;
    }
};
</script>
