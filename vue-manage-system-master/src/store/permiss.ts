import { defineStore } from 'pinia';

interface ObjectList {
    [key: string]: string[];
}

export const usePermissStore = defineStore('permiss', {
    state: () => {
        const defaultList: ObjectList = {
            admin: [
                '0',
                '1',
                '11',
                '12',
                '13',
                '4',
                '41',
                '42',
                '8',
                '81',
                '82',
                '83',
                '84',
                '85',
                '86',
                '87',
                '7',
                '6',
                '61',
                '62',
                '63',
                '64',
                '65',
                '66',
            ],
            user: ['0', '1', '11', '12', '13'],
        };
        const username = localStorage.getItem('vuems_name');
        console.log(username);
        return {
            key: (username == 'admin' ? defaultList.admin : defaultList.user) as string[],
            defaultList,
        };
    },
    actions: {
        handleSet(val: string[]) {
            this.key = val;
        },
    },
});
