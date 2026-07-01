export interface AiNewsLinkDef {
    id: string;
    url: string;
    /** 浏览器标签页同款 favicon，直连各站 */
    icon: string;
    /** 图标加载失败时的彩色首字兜底 */
    letter: string;
    color: string;
}

export const internationalLinkDefs: AiNewsLinkDef[] = [
    {
        id: 'openai',
        url: 'https://openai.com/news/',
        icon: 'https://openai.com/favicon.ico',
        letter: 'O',
        color: '#10A37F',
    },
    {
        id: 'anthropic',
        url: 'https://www.anthropic.com/news',
        icon: 'https://www.anthropic.com/favicon.ico',
        letter: 'A',
        color: '#CC785C',
    },
    {
        id: 'deepmind',
        url: 'https://deepmind.google/discover/blog/',
        icon: 'https://deepmind.google/favicon.ico',
        letter: 'D',
        color: '#4285F4',
    },
    {
        id: 'metaAi',
        url: 'https://ai.meta.com/blog/',
        icon: 'https://static.xx.fbcdn.net/rsrc.php/yB/r/qOSYt3pbp0K.ico',
        letter: 'M',
        color: '#0668E1',
    },
    {
        id: 'xAi',
        url: 'https://x.ai/news',
        icon: 'https://x.ai/favicon.ico',
        letter: 'X',
        color: '#000000',
    },
    {
        id: 'huggingface',
        url: 'https://huggingface.co/blog',
        icon: 'https://huggingface.co/favicon.ico',
        letter: 'H',
        color: '#FFD21E',
    },
    {
        id: 'huggingfacePapers',
        url: 'https://huggingface.co/papers',
        icon: 'https://huggingface.co/favicon.ico',
        letter: 'P',
        color: '#FFD21E',
    },
    {
        id: 'langchain',
        url: 'https://www.langchain.com/blog',
        icon: 'https://www.langchain.com/favicon.ico',
        letter: 'L',
        color: '#1C3C3C',
    },
    {
        id: 'llamaindex',
        url: 'https://www.llamaindex.ai/blog',
        icon: 'https://www.llamaindex.ai/favicon.ico',
        letter: 'Li',
        color: '#7C3AED',
    },
    {
        id: 'nvidiaBlog',
        url: 'https://developer.nvidia.com/blog',
        icon: 'https://developer.nvidia.com/favicon.ico',
        letter: 'N',
        color: '#76B900',
    },
    {
        id: 'arxiv',
        url: 'https://arxiv.org/list/cs.AI/recent',
        icon: 'https://arxiv.org/static/browse/0.3.4/images/icons/favicon-32x32.png',
        letter: 'ar',
        color: '#B31B1B',
    },
    {
        id: 'googleAi',
        url: 'https://blog.google/technology/ai/',
        icon: 'https://www.google.com/favicon.ico',
        letter: 'G',
        color: '#4285F4',
    },
    {
        id: 'microsoftAi',
        url: 'https://blogs.microsoft.com/ai/',
        icon: 'https://www.microsoft.com/favicon.ico',
        letter: 'M',
        color: '#00A4EF',
    },
    {
        id: 'mitTr',
        url: 'https://www.technologyreview.com/topic/artificial-intelligence/',
        icon: 'https://www.technologyreview.com/favicon.ico',
        letter: 'T',
        color: '#000000',
    },
    {
        id: 'hnAi',
        url: 'https://hn.algolia.com/?q=AI',
        icon: 'https://news.ycombinator.com/favicon.ico',
        letter: 'Y',
        color: '#FF6600',
    },
];

export const domesticLinkDefs: AiNewsLinkDef[] = [
    {
        id: 'jiqizhixin',
        url: 'https://www.jiqizhixin.com/',
        icon: 'https://www.jiqizhixin.com/favicon.ico',
        letter: '机',
        color: '#1E88E5',
    },
    {
        id: 'qbitai',
        url: 'https://www.qbitai.com/',
        icon: 'https://www.qbitai.com/favicon.ico',
        letter: '量',
        color: '#1565C0',
    },
    {
        id: 'zhidx',
        url: 'https://www.zhidx.com/',
        icon: 'https://www.zhidx.com/favicon.ico',
        letter: '智',
        color: '#E53935',
    },
    {
        id: 'leiphone',
        url: 'https://www.leiphone.com/category/ai',
        icon: 'https://www.leiphone.com/favicon.ico',
        letter: '雷',
        color: '#D32F2F',
    },
    {
        id: 'kr36',
        url: 'https://36kr.com/information/AI/',
        icon: 'https://36kr.com/favicon.ico',
        letter: '36',
        color: '#286EFA',
    },
    {
        id: 'infoq',
        url: 'https://www.infoq.cn/',
        icon: 'https://www.infoq.cn/favicon.ico',
        letter: 'Q',
        color: '#00B388',
    },
];
