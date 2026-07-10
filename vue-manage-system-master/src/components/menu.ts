import { Menus } from '@/types/menu';

export const menuData: Menus[] = [
    {
        id: '0',
        titleKey: 'menu.dashboard',
        index: '/dashboard',
        icon: 'Odometer',
    },
    {
        id: '1',
        titleKey: 'menu.system',
        index: '1',
        icon: 'HomeFilled',
        children: [
            {
                id: '11',
                pid: '1',
                index: '/system-user',
                titleKey: 'menu.systemUser',
            },
            {
                id: '12',
                pid: '1',
                index: '/system-role',
                titleKey: 'menu.systemRole',
            },
            {
                id: '13',
                pid: '1',
                index: '/system-menu',
                titleKey: 'menu.systemMenu',
            },
        ],
    },
    {
        id: '8',
        titleKey: 'menu.business',
        index: '8',
        icon: 'DataAnalysis',
        children: [
            {
                id: '90',
                pid: '8',
                index: '/system-llm-usage',
                titleKey: 'menu.systemLlmUsage',
            },
            {
                id: '80',
                pid: '8',
                index: '/demo-ai-news',
                titleKey: 'menu.demoAiNews',
            },
            {
                id: '81',
                pid: '8',
                index: '/demo-complaints',
                titleKey: 'menu.demoComplaints',
            },
            {
                id: '82',
                pid: '8',
                index: '/demo-rag',
                titleKey: 'menu.demoRag',
            },
            {
                id: '83',
                pid: '8',
                index: '/demo-ai-chat',
                titleKey: 'menu.demoAiChat',
            },
            {
                id: '84',
                pid: '8',
                index: '/demo-agent',
                titleKey: 'menu.demoAgent',
            },
            {
                id: '85',
                pid: '8',
                index: '/demo-meeting',
                titleKey: 'menu.demoMeeting',
            },
            {
                id: '86',
                pid: '8',
                index: '/demo-smart-route',
                titleKey: 'menu.demoSmartRoute',
            },
            {
                id: '87',
                pid: '8',
                index: '/demo-attendance',
                titleKey: 'menu.demoAttendance',
            },
            {
                id: '88',
                pid: '8',
                index: '/demo-cobol-migrate',
                titleKey: 'menu.demoCobolMigrate',
            },
            {
                id: '89',
                pid: '8',
                index: '/modules-zha-jinhua',
                titleKey: 'menu.demoZhaJinhua',
            },
            {
                id: '91',
                pid: '8',
                index: '/modules-insight',
                titleKey: 'menu.demoInsight',
            },
        ],
    },
    {
        id: '7',
        icon: 'Brush',
        index: '/theme',
        titleKey: 'menu.theme',
    },
    {
        id: '6',
        icon: 'DocumentAdd',
        index: '6',
        titleKey: 'menu.extraPages',
        children: [
            {
                id: '61',
                pid: '6',
                index: '/ucenter',
                titleKey: 'menu.ucenter',
            },
            {
                id: '62',
                pid: '6',
                index: '/login',
                titleKey: 'menu.login',
            },
            {
                id: '63',
                pid: '6',
                index: '/register',
                titleKey: 'menu.register',
            },
            {
                id: '64',
                pid: '6',
                index: '/reset-pwd',
                titleKey: 'menu.resetPwd',
            },
            {
                id: '65',
                pid: '6',
                index: '/403',
                titleKey: '403',
            },
            {
                id: '66',
                pid: '6',
                index: '/404',
                titleKey: '404',
            },
        ],
    },
];
