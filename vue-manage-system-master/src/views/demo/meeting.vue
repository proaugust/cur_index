<template>
    <div class="container meeting-page">
        <el-card shadow="hover">
            <template #header>
                <div class="page-header">
                    <span class="page-title">{{ t('pages.meeting.title') }}</span>
                    <FeatureIntroIcon
                        page-key="meeting"
                        section-key="page"
                        :intros="intros"
                        :title="t('pages.meeting.title')"
                        @saved="setIntro"
                    />
                </div>
            </template>

            <div class="input-section">
                <div class="section-label">{{ t('pages.meeting.style') }}</div>
                <el-radio-group v-model="organizeStyle" size="small" :disabled="loading">
                    <el-radio-button value="concise">{{ t('pages.meeting.styleConcise') }}</el-radio-button>
                    <el-radio-button value="formal">{{ t('pages.meeting.styleFormal') }}</el-radio-button>
                </el-radio-group>
                <div class="section-label input-label">{{ t('pages.meeting.rawText') }}</div>
                <el-input
                    v-model="inputText"
                    type="textarea"
                    :rows="10"
                    :placeholder="t('pages.meeting.placeholder')"
                    :disabled="loading"
                />
                <div class="action-bar">
                    <el-button type="primary" :loading="loading" :disabled="!inputText.trim()" @click="handleOrganize">
                        {{ t('common.organize') }}
                    </el-button>
                    <el-button :disabled="loading || !inputText" @click="handleClear">{{ t('common.clear') }}</el-button>
                </div>
            </div>

            <el-divider />

            <div class="output-section">
                <div class="section-label">{{ t('pages.meeting.result') }}</div>
                <div v-if="organizedText" class="result-box">{{ organizedText }}</div>
                <el-empty v-else :description="t('pages.meeting.empty')" :image-size="80" />
            </div>
        </el-card>
    </div>
</template>

<script setup lang="ts" name="demo-meeting">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import FeatureIntroIcon from '@/components/feature-intro-icon.vue';
import { useFeatureIntros } from '@/composables/useFeatureIntros';
import { useCachedRef } from '@/composables/useFormCache';
import { organizeMeeting } from '@/api';

const { t } = useI18n();
const { intros, setIntro } = useFeatureIntros('meeting');

const DEFAULT_MEETING_TEXT = `张三： 12点了，今天中午吃啥？老规矩，去楼下吃快餐？
李四： 别点快餐了，油大还腻。今天出太阳了，不如走远点，去后面那条街吃那家新开的黄焖鸡？
王五： 黄焖鸡太重口味了，我最近减脂，想吃点清淡的。要不去吃便利店的沙拉，或者去吃那家潮汕牛肉粿条？
赵六： 粿条分量太少，下午两点就得饿。我想吃点热乎的、能吃饱的。听说附近开了一家石锅拌饭，有肉有菜，分量挺足，王五你也可以少放点酱。
钱七： 石锅拌饭不错，但我看排队人挺多的。我们一共五个人，要不直接在软件上拼单点个酸菜鱼外卖？在休息区吃，还省得出去晒太阳。
张三： 别点外卖了，送来都凉了。既然大家意见不统一，赵六说的石锅拌饭和王五说的潮汕粿条在同一条街上。我们直接过去，想吃拌饭的坐左边，想吃粿条的坐右边，步行五分钟，正好活动一下。
李四： 行，那快走吧，再晚没位置了。
众人： 走走走！`;

const inputText = useCachedRef('meeting:inputText', DEFAULT_MEETING_TEXT);
const organizeStyle = useCachedRef<'concise' | 'formal'>('meeting:organizeStyle', 'formal');
const organizedText = ref('');
const loading = ref(false);

const handleOrganize = async () => {
    const text = inputText.value.trim();
    if (!text) return;

    loading.value = true;
    organizedText.value = '';
    try {
        const res = await organizeMeeting({ text, style: organizeStyle.value });
        organizedText.value = res.data.organized_text ?? '';
    } catch (err: unknown) {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        ElMessage.error(typeof msg === 'string' ? msg : '整理失败，请稍后重试');
    } finally {
        loading.value = false;
    }
};

const handleClear = () => {
    organizedText.value = '';
};
</script>

<style scoped>
.meeting-page .page-header {
    display: inline-flex;
    align-items: center;
}

.meeting-page .page-title {
    font-size: 16px;
    font-weight: 600;
}

.section-label {
    margin-bottom: 8px;
    font-size: 14px;
    font-weight: 500;
}

.input-label {
    margin-top: 16px;
}

.action-bar {
    margin-top: 12px;
    display: flex;
    gap: 8px;
}

.result-box {
    min-height: 120px;
    padding: 16px;
    border: 1px solid var(--el-border-color-light);
    border-radius: 4px;
    background: var(--el-fill-color-blank);
    white-space: pre-wrap;
    line-height: 1.7;
    font-size: 14px;
}
</style>
