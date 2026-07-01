<template>
    <div class="login-bg">
        <div class="login-container">
            <div class="login-header">
                <img class="logo mr10" src="../../assets/img/logo.svg" alt="" />
                <div class="login-title">{{ t('pages.login.title') }}</div>
            </div>
            <el-form :model="param" :rules="rules" ref="login" size="large">
                <el-form-item prop="username">
                    <el-input v-model="param.username" :placeholder="t('pages.login.username')">
                        <template #prepend>
                            <el-icon>
                                <User />
                            </el-icon>
                        </template>
                    </el-input>
                </el-form-item>
                <el-form-item prop="password">
                    <el-input
                        type="password"
                        :placeholder="t('pages.login.password')"
                        v-model="param.password"
                        @keyup.enter="submitForm(login)"
                    >
                        <template #prepend>
                            <el-icon>
                                <Lock />
                            </el-icon>
                        </template>
                    </el-input>
                </el-form-item>
                <div class="pwd-tips">
                    <el-checkbox class="pwd-checkbox" v-model="checked" :label="t('pages.login.remember')" />
                    <el-link type="primary" @click="$router.push('/reset-pwd')">{{ t('pages.login.forgot') }}</el-link>
                </div>
                <el-button class="login-btn" type="primary" size="large" @click="submitForm(login)">{{ t('pages.login.submit') }}</el-button>
                <p class="login-tips">{{ t('pages.login.tips') }}</p>
            </el-form>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useTabsStore } from '@/store/tabs';
import { usePermissStore } from '@/store/permiss';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import type { FormInstance, FormRules } from 'element-plus';
import { login as loginApi } from '@/api';

const { t } = useI18n();

interface LoginInfo {
    username: string;
    password: string;
}

const lgStr = localStorage.getItem('login-param');
const defParam = lgStr ? JSON.parse(lgStr) : null;
const checked = ref(lgStr ? true : false);

const router = useRouter();
const param = reactive<LoginInfo>({
    username: defParam ? defParam.username : 'user1',
    password: defParam ? defParam.password : '111111',
});

const rules = computed<FormRules>(() => ({
    username: [
        {
            required: true,
            message: t('pages.login.usernameRequired'),
            trigger: 'blur',
        },
    ],
    password: [{ required: true, message: t('pages.login.passwordRequired'), trigger: 'blur' }],
}));
const permiss = usePermissStore();
const login = ref<FormInstance>();
const submitForm = (formEl: FormInstance | undefined) => {
    if (!formEl) return;
    formEl.validate(async (valid: boolean) => {
        if (!valid) {
            ElMessage.error(t('pages.login.loginFailed'));
            return false;
        }
        try {
            const res = await loginApi({
                username: param.username,
                password: param.password,
            });
            const data = res.data;
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('vuems_name', data.user.username);
            permiss.handleSet(data.permissions);
            ElMessage.success(t('pages.login.loginSuccess'));
            router.push('/');
            if (checked.value) {
                localStorage.setItem('login-param', JSON.stringify({ username: param.username, password: param.password }));
            } else {
                localStorage.removeItem('login-param');
            }
        } catch {
            ElMessage.error(t('pages.login.authFailed'));
        }
    });
};

const tabs = useTabsStore();
tabs.clearTabs();
</script>

<style scoped>
.login-bg {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100vh;
    background: url(../../assets/img/login-bg.jpg) center/cover no-repeat;
}

.login-header {
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 40px;
}

.logo {
    width: 35px;
}

.login-title {
    font-size: 22px;
    color: #333;
    font-weight: bold;
}

.login-container {
    width: 450px;
    border-radius: 5px;
    background: #fff;
    padding: 40px 50px 50px;
    box-sizing: border-box;
}

.pwd-tips {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 14px;
    margin: -10px 0 10px;
    color: #787878;
}

.pwd-checkbox {
    height: auto;
}

.login-btn {
    display: block;
    width: 100%;
}

.login-tips {
    font-size: 12px;
    color: #999;
}

.login-text {
    display: flex;
    align-items: center;
    margin-top: 20px;
    font-size: 14px;
    color: #787878;
}
</style>
