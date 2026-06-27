import { onMounted, ref } from 'vue';
import { getFeatureIntros } from '@/api';

/** section_key -> 介绍正文（含空字符串） */
export type FeatureIntroMap = Record<string, string>;

export function useFeatureIntros(pageKey: string) {
    const intros = ref<FeatureIntroMap>({});
    const loading = ref(false);

    const load = async () => {
        loading.value = true;
        try {
            const res = await getFeatureIntros(pageKey);
            const map: FeatureIntroMap = {};
            for (const row of res.data ?? []) {
                map[row.section_key] = row.content ?? '';
            }
            intros.value = map;
        } catch {
            intros.value = {};
        } finally {
            loading.value = false;
        }
    };

    const setIntro = (sectionKey: string, content: string) => {
        intros.value = { ...intros.value, [sectionKey]: content };
    };

    onMounted(load);

    return { intros, loading, reload: load, setIntro };
}
