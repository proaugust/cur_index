import { createRouter, createWebHashHistory, RouteRecordRaw } from 'vue-router';
import { usePermissStore } from '../store/permiss';
import { fetchMe } from '../api';
import Home from '../views/home.vue';
import NProgress from 'nprogress';
import 'nprogress/nprogress.css';

const routes: RouteRecordRaw[] = [
    {
        path: '/',
        redirect: '/dashboard',
    },
    {
        path: '/',
        name: 'Home',
        component: Home,
        children: [
            {
                path: '/dashboard',
                name: 'dashboard',
                meta: {
                    titleKey: 'route.dashboard',
                    title: '系统首页',
                },
                component: () => import(/* webpackChunkName: "dashboard" */ '../views/dashboard.vue'),
            },
            {
                path: '/system-llm-usage',
                name: 'system-llm-usage',
                meta: {
                    titleKey: 'route.systemLlmUsage',
                    title: 'LLM 用量',
                    permiss: '90',
                },
                component: () => import(/* webpackChunkName: "system-llm-usage" */ '../views/system/llm-usage.vue'),
            },
            {
                path: '/system-error-logs',
                name: 'system-error-logs',
                meta: {
                    titleKey: 'route.systemErrorLogs',
                    title: '错误日志',
                    permiss: '92',
                },
                component: () => import(/* webpackChunkName: "system-error-logs" */ '../views/system/error-logs.vue'),
            },
            {
                path: '/demo-ai-news',
                name: 'demo-ai-news',
                meta: {
                    titleKey: 'route.demoAiNews',
                    title: 'AI 资讯导航',
                    permiss: '80',
                },
                component: () => import(/* webpackChunkName: "demo-ai-news" */ '../views/demo/ai-news-links.vue'),
            },
            {
                path: '/demo-complaints',
                name: 'demo-complaints',
                meta: {
                    titleKey: 'route.demoComplaints',
                    title: '投诉归类演示',
                    permiss: '81',
                },
                component: () => import(/* webpackChunkName: "demo-complaints" */ '../views/demo/complaints.vue'),
            },
            {
                path: '/demo-rag',
                redirect: '/demo-rag/document',
            },
            {
                path: '/demo-rag/document',
                name: 'demo-rag-document',
                meta: {
                    titleKey: 'pages.rag.documentSection',
                    title: '通用文档库',
                    permiss: '82',
                },
                component: () => import(/* webpackChunkName: "demo-rag-document" */ '../views/demo/rag/document.vue'),
            },
            {
                path: '/demo-rag/corpora',
                name: 'demo-rag-corpora',
                meta: {
                    titleKey: 'pages.rag.corporaSection',
                    title: '业务资料库',
                    permiss: '82',
                },
                component: () => import(/* webpackChunkName: "demo-rag-corpora" */ '../views/demo/rag/corpora.vue'),
            },
            {
                path: '/demo-rag/nl2sql',
                name: 'demo-rag-nl2sql',
                meta: {
                    titleKey: 'pages.rag.nl2sqlSection',
                    title: '问数 NL2SQL',
                    permiss: '82',
                },
                component: () => import(/* webpackChunkName: "demo-rag-nl2sql" */ '../views/demo/rag/nl2sql.vue'),
            },
            {
                path: '/demo-rag/longdoc',
                name: 'demo-rag-longdoc',
                meta: {
                    titleKey: 'pages.rag.longdocSection',
                    title: '长文档审计',
                    permiss: '82',
                },
                component: () => import(/* webpackChunkName: "demo-rag-longdoc" */ '../views/demo/rag/longdoc.vue'),
            },
            {
                path: '/demo-rag/web',
                name: 'demo-rag-web',
                meta: {
                    titleKey: 'pages.rag.webSection',
                    title: '时效 Web',
                    permiss: '82',
                },
                component: () => import(/* webpackChunkName: "demo-rag-web" */ '../views/demo/rag/web.vue'),
            },
            {
                path: '/demo-rag/agentic',
                redirect: '/demo-agent/agentic',
            },
            {
                path: '/demo-ai-chat',
                name: 'demo-ai-chat',
                meta: {
                    titleKey: 'route.demoAiChat',
                    title: 'AI训练提问',
                    permiss: '83',
                },
                component: () => import(/* webpackChunkName: "demo-ai-chat" */ '../views/demo/ai-chat.vue'),
            },
            {
                path: '/demo-agent',
                redirect: '/demo-agent/native',
            },
            {
                path: '/demo-agent/native',
                name: 'demo-agent-native',
                meta: {
                    titleKey: 'pages.agent.nativeSection',
                    title: '原生编排',
                    permiss: '84',
                },
                component: () => import(/* webpackChunkName: "demo-agent-native" */ '../views/demo/agent/native.vue'),
            },
            {
                path: '/demo-agent/langchain',
                name: 'demo-agent-langchain',
                meta: {
                    titleKey: 'pages.agent.langchainSection',
                    title: 'LangChain / LangGraph',
                    permiss: '84',
                },
                component: () =>
                    import(/* webpackChunkName: "demo-agent-langchain" */ '../views/demo/agent/langchain.vue'),
            },
            {
                path: '/demo-agent/autogen',
                name: 'demo-agent-autogen',
                meta: {
                    titleKey: 'pages.agent.autogenSection',
                    title: 'AutoGen',
                    permiss: '84',
                },
                component: () => import(/* webpackChunkName: "demo-agent-autogen" */ '../views/demo/agent/autogen.vue'),
            },
            {
                path: '/demo-agent/crewai',
                name: 'demo-agent-crewai',
                meta: {
                    titleKey: 'pages.agent.crewaiSection',
                    title: 'CrewAI',
                    permiss: '84',
                },
                component: () => import(/* webpackChunkName: "demo-agent-crewai" */ '../views/demo/agent/crewai.vue'),
            },
            {
                path: '/demo-agent/agentic',
                name: 'demo-agent-agentic',
                meta: {
                    titleKey: 'pages.agent.agenticSection',
                    title: '多步 Agent',
                    permiss: '84',
                },
                component: () =>
                    import(/* webpackChunkName: "demo-agent-agentic" */ '../views/demo/agent/agentic.vue'),
            },
            {
                path: '/demo-meeting',
                name: 'demo-meeting',
                meta: {
                    titleKey: 'route.demoMeeting',
                    title: '会议整理',
                    permiss: '85',
                },
                component: () => import(/* webpackChunkName: "demo-meeting" */ '../views/demo/meeting.vue'),
            },
            {
                path: '/demo-smart-route',
                name: 'demo-smart-route',
                meta: {
                    titleKey: 'route.demoSmartRoute',
                    title: '智能路由',
                    permiss: '86',
                },
                component: () => import(/* webpackChunkName: "demo-smart-route" */ '../views/demo/smart-route.vue'),
            },
            {
                path: '/demo-attendance',
                name: 'demo-attendance',
                meta: {
                    titleKey: 'route.demoAttendance',
                    title: '人脸打卡',
                    permiss: '87',
                },
                component: () => import(/* webpackChunkName: "demo-attendance" */ '../views/demo/attendance.vue'),
            },
            {
                path: '/modules-attendance',
                redirect: '/demo-attendance',
            },
            {
                path: '/demo-cobol-migrate',
                name: 'demo-cobol-migrate',
                meta: {
                    titleKey: 'route.demoCobolMigrate',
                    title: 'COBOL to Java',
                    permiss: '88',
                },
                component: () => import(/* webpackChunkName: "demo-cobol-migrate" */ '../views/demo/cobol-migrate.vue'),
            },
            {
                path: '/modules-zha-jinhua',
                name: 'modules-zha-jinhua',
                meta: {
                    titleKey: 'route.demoZhaJinhua',
                    title: '赌博agent 游戏',
                    permiss: '89',
                },
                component: () => import(/* webpackChunkName: "modules-zha-jinhua" */ '../views/demo/zha-jinhua.vue'),
            },
            {
                path: '/demo-zha-jinhua',
                redirect: '/modules-zha-jinhua',
            },
            {
                path: '/modules-insight',
                name: 'modules-insight',
                meta: {
                    titleKey: 'route.demoInsight',
                    title: 'Customer Insight AI Platform',
                    permiss: '91',
                },
                component: () => import(/* webpackChunkName: "modules-insight" */ '../views/demo/insight/index.vue'),
            },
            {
                path: '/demo-insight',
                redirect: '/modules-insight',
            },
            {
                path: '/system-user',
                name: 'system-user',
                meta: {
                    title: '用户管理',
                    permiss: '11',
                },
                component: () => import(/* webpackChunkName: "system-user" */ '../views/system/user.vue'),
            },
            {
                path: '/system-role',
                name: 'system-role',
                meta: {
                    title: '角色管理',
                    permiss: '12',
                },
                component: () => import(/* webpackChunkName: "system-role" */ '../views/system/role.vue'),
            },
            {
                path: '/system-menu',
                name: 'system-menu',
                meta: {
                    title: '菜单管理',
                    permiss: '13',
                },
                component: () => import(/* webpackChunkName: "system-menu" */ '../views/system/menu.vue'),
            },
            {
                path: '/system-login-logs',
                name: 'system-login-logs',
                meta: {
                    titleKey: 'route.systemLoginLogs',
                    title: '登录记录',
                    permiss: '14',
                },
                component: () => import(/* webpackChunkName: "system-login-logs" */ '../views/system/login-logs.vue'),
            },
            {
                path: '/system-api-access',
                name: 'system-api-access',
                meta: {
                    titleKey: 'route.systemApiAccess',
                    title: '接口访问',
                    permiss: '15',
                },
                component: () => import(/* webpackChunkName: "system-api-access" */ '../views/system/api-access.vue'),
            },
            {
                path: '/table',
                name: 'basetable',
                meta: {
                    title: '基础表格',
                    permiss: '31',
                },
                component: () => import(/* webpackChunkName: "table" */ '../views/table/basetable.vue'),
            },
            {
                path: '/table-editor',
                name: 'table-editor',
                meta: {
                    title: '可编辑表格',
                    permiss: '32',
                },
                component: () => import(/* webpackChunkName: "table-editor" */ '../views/table/table-editor.vue'),
            },
            {
                path: '/schart',
                name: 'schart',
                meta: {
                    title: 'schart图表',
                    permiss: '41',
                },
                component: () => import(/* webpackChunkName: "schart" */ '../views/chart/schart.vue'),
            },
            {
                path: '/echarts',
                name: 'echarts',
                meta: {
                    title: 'echarts图表',
                    permiss: '42',
                },
                component: () => import(/* webpackChunkName: "echarts" */ '../views/chart/echarts.vue'),
            },

            {
                path: '/icon',
                name: 'icon',
                meta: {
                    title: '图标',
                    permiss: '5',
                },
                component: () => import(/* webpackChunkName: "icon" */ '../views/pages/icon.vue'),
            },
            {
                path: '/ucenter',
                name: 'ucenter',
                meta: {
                    titleKey: 'route.ucenter',
                    title: '个人中心',
                },
                component: () => import(/* webpackChunkName: "ucenter" */ '../views/pages/ucenter.vue'),
            },
            {
                path: '/editor',
                name: 'editor',
                meta: {
                    title: '富文本编辑器',
                    permiss: '291',
                },
                component: () => import(/* webpackChunkName: "editor" */ '../views/pages/editor.vue'),
            },
            {
                path: '/markdown',
                name: 'markdown',
                meta: {
                    title: 'markdown编辑器',
                    permiss: '292',
                },
                component: () => import(/* webpackChunkName: "markdown" */ '../views/pages/markdown.vue'),
            },
            {
                path: '/export',
                name: 'export',
                meta: {
                    title: '导出Excel',
                    permiss: '34',
                },
                component: () => import(/* webpackChunkName: "export" */ '../views/table/export.vue'),
            },
            {
                path: '/import',
                name: 'import',
                meta: {
                    title: '导入Excel',
                    permiss: '33',
                },
                component: () => import(/* webpackChunkName: "import" */ '../views/table/import.vue'),
            },
            {
                path: '/theme',
                name: 'theme',
                meta: {
                    titleKey: 'route.theme',
                    title: '主题设置',
                    permiss: '7',
                },
                component: () => import(/* webpackChunkName: "theme" */ '../views/pages/theme.vue'),
            },
            {
                path: '/calendar',
                name: 'calendar',
                meta: {
                    title: '日历',
                    permiss: '24',
                },
                component: () => import(/* webpackChunkName: "calendar" */ '../views/element/calendar.vue'),
            },
            {
                path: '/watermark',
                name: 'watermark',
                meta: {
                    title: '水印',
                    permiss: '25',
                },
                component: () => import(/* webpackChunkName: "watermark" */ '../views/element/watermark.vue'),
            },
            {
                path: '/carousel',
                name: 'carousel',
                meta: {
                    title: '走马灯',
                    permiss: '23',
                },
                component: () => import(/* webpackChunkName: "carousel" */ '../views/element/carousel.vue'),
            },
            {
                path: '/tour',
                name: 'tour',
                meta: {
                    title: '分步引导',
                    permiss: '26',
                },
                component: () => import(/* webpackChunkName: "tour" */ '../views/element/tour.vue'),
            },
            {
                path: '/steps',
                name: 'steps',
                meta: {
                    title: '步骤条',
                    permiss: '27',
                },
                component: () => import(/* webpackChunkName: "steps" */ '../views/element/steps.vue'),
            },
            {
                path: '/form',
                name: 'forms',
                meta: {
                    title: '表单',
                    permiss: '21',
                },
                component: () => import(/* webpackChunkName: "form" */ '../views/element/form.vue'),
            },
            {
                path: '/upload',
                name: 'upload',
                meta: {
                    title: '上传',
                    permiss: '22',
                },
                component: () => import(/* webpackChunkName: "upload" */ '../views/element/upload.vue'),
            },
            {
                path: '/statistic',
                name: 'statistic',
                meta: {
                    title: '统计',
                    permiss: '28',
                },
                component: () => import(/* webpackChunkName: "statistic" */ '../views/element/statistic.vue'),
            },
        ],
    },
    {
        path: '/login',
        meta: {
            titleKey: 'route.login',
            title: '登录',
            noAuth: true,
        },
        component: () => import(/* webpackChunkName: "login" */ '../views/pages/login.vue'),
    },
    {
        path: '/register',
        meta: {
            title: '注册',
            noAuth: true,
        },
        component: () => import(/* webpackChunkName: "register" */ '../views/pages/register.vue'),
    },
    {
        path: '/reset-pwd',
        meta: {
            title: '重置密码',
            noAuth: true,
        },
        component: () => import(/* webpackChunkName: "reset-pwd" */ '../views/pages/reset-pwd.vue'),
    },
    {
        path: '/403',
        meta: {
            title: '没有权限',
            noAuth: true,
        },
        component: () => import(/* webpackChunkName: "403" */ '../views/pages/403.vue'),
    },
    {
        path: '/404',
        meta: {
            title: '找不到页面',
            noAuth: true,
        },
        component: () => import(/* webpackChunkName: "404" */ '../views/pages/404.vue'),
    },
    { path: '/:path(.*)', redirect: '/404' },
];

const router = createRouter({
    history: createWebHashHistory(),
    routes,
});

let verifiedToken: string | null = null;

function clearClientSession() {
    verifiedToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('vuems_name');
    usePermissStore().clear();
}

router.beforeEach(async (to, from, next) => {
    NProgress.start();
    const token = localStorage.getItem('access_token');
    const permiss = usePermissStore();

    if (to.meta.noAuth === true) {
        next();
        return;
    }

    if (!token) {
        next({ path: '/login', replace: true });
        return;
    }

    if (token !== verifiedToken) {
        try {
            const res = await fetchMe();
            const data = res.data;
            if (!data?.user?.username) {
                throw new Error('not logged in');
            }
            verifiedToken = token;
            localStorage.setItem('vuems_name', data.user.username);
            if (data.permissions?.length) {
                permiss.handleSet(data.permissions);
            }
        } catch {
            clearClientSession();
            next({ path: '/login', replace: true });
            return;
        }
    }

    if (typeof to.meta.permiss == 'string' && !permiss.hasRoutePermiss(to.meta.permiss)) {
        next('/403');
    } else {
        next();
    }
});

router.afterEach(() => {
    NProgress.done();
});

export default router;
