<template>
    <div class="container meeting-page">
        <el-card shadow="hover">
            <template #header>
                <div class="page-header">
                    <span class="page-title">会议整理</span>
                    <span class="page-subtitle">输入杂乱会议记录，由大模型整理为有条理、有结论的纪要</span>
                </div>
            </template>

            <div class="input-section">
                <div class="section-label">原始文字</div>
                <el-input
                    v-model="inputText"
                    type="textarea"
                    :rows="10"
                    placeholder="粘贴会议速记、语音转写或零散讨论内容……"
                    :disabled="loading"
                />
                <div class="action-bar">
                    <el-button type="primary" :loading="loading" :disabled="!inputText.trim()" @click="handleOrganize">
                        整理
                    </el-button>
                    <el-button :disabled="loading || !inputText" @click="handleClear">清空</el-button>
                </div>
            </div>

            <el-divider />

            <div class="output-section">
                <div class="section-label">整理结果</div>
                <div v-if="organizedText" class="result-box">{{ organizedText }}</div>
                <el-empty v-else description="整理后的纪要将显示在这里" :image-size="80" />
            </div>
        </el-card>
    </div>
</template>

<script setup lang="ts" name="demo-meeting">
import { ref } from 'vue';
import { ElMessage } from 'element-plus';
import { organizeMeeting } from '@/api';

const inputText = ref(`张三： 12点了，今天中午吃啥？老规矩，去楼下吃快餐？
李四： 别点快餐了，油大还腻。今天出太阳了，不如走远点，去后面那条街吃那家新开的黄焖鸡？
王五： 黄焖鸡太重口味了，我最近减脂，想吃点清淡的。要不去吃便利店的沙拉，或者去吃那家潮汕牛肉粿条？
赵六： 粿条分量太少，下午两点就得饿。我想吃点热乎的、能吃饱的。听说附近开了一家石锅拌饭，有肉有菜，分量挺足，王五你也可以少放点酱。
钱七： 石锅拌饭不错，但我看排队人挺多的。我们一共五个人，要不直接在软件上拼单点个酸菜鱼外卖？在休息区吃，还省得出去晒太阳。
张三： 别点外卖了，送来都凉了。既然大家意见不统一，赵六说的石锅拌饭和王五说的潮汕粿条在同一条街上。我们直接过去，想吃拌饭的坐左边，想吃粿条的坐右边，步行五分钟，正好活动一下。
李四： 行，那快走吧，再晚没位置了。
王五、赵六、钱七： 没问题，听张三的，出发！`);
const organizedText = ref('');
const loading = ref(false);

const handleOrganize = async () => {
    const text = inputText.value.trim();
    if (!text) return;

    loading.value = true;
    try {
        const res = await organizeMeeting({ text });
        organizedText.value = res.data.organized_text;
    } catch (err: unknown) {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        ElMessage.error(typeof msg === 'string' ? msg : '整理失败，请稍后重试');
    } finally {
        loading.value = false;
    }
};

const handleClear = () => {
    inputText.value = '';
    organizedText.value = '';
};
</script>

<style scoped>
.meeting-page .page-header {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.meeting-page .page-title {
    font-size: 16px;
    font-weight: 600;
}

.meeting-page .page-subtitle {
    font-size: 13px;
    color: var(--el-text-color-secondary);
}

.section-label {
    margin-bottom: 8px;
    font-size: 14px;
    font-weight: 500;
}

.action-bar {
    margin-top: 12px;
    display: flex;
    gap: 8px;
}

.result-box {
    min-height: 200px;
    padding: 16px;
    border: 1px solid var(--el-border-color-light);
    border-radius: 4px;
    background: var(--el-fill-color-blank);
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.7;
    font-size: 14px;
}
</style>
