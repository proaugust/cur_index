<template>
    <div class="container attendance-page">
        <el-row :gutter="20">
            <el-col :xs="24" :lg="12">
                <el-card shadow="hover" class="camera-card">
                    <template #header>
                        <div class="card-header">
                            <div>
                                <div class="page-title">人脸打卡</div>
                                <div class="page-subtitle">检测到人脸后自动打卡，可调整识别频率与去重策略</div>
                            </div>
                            <el-tag :type="cameraOn ? 'success' : 'info'" size="small">
                                {{ cameraOn ? '摄像头已开启' : '摄像头未开启' }}
                            </el-tag>
                        </div>
                    </template>

                    <div class="video-wrap">
                        <video ref="videoRef" class="video" autoplay muted playsinline />
                        <canvas ref="canvasRef" class="overlay" />
                        <div v-if="modelsLoading" class="video-mask">正在加载识别模型…</div>
                        <div v-else-if="!cameraOn" class="video-mask">点击「打开摄像头」开始打卡</div>
                    </div>

                    <div class="tuning-panel">
                        <div class="tuning-head">
                            <span>摄像头分辨率</span>
                            <span class="tuning-hint">
                                {{ currentResolution.hint }}
                                <template v-if="actualResolution"> · 实际 {{ actualResolution }}</template>
                            </span>
                        </div>
                        <el-select
                            v-model="resolutionPresetId"
                            class="resolution-select"
                            :disabled="startingCamera"
                            @change="handleResolutionChange"
                        >
                            <el-option
                                v-for="item in RESOLUTION_PRESETS"
                                :key="item.id"
                                :label="item.label"
                                :value="item.id"
                            />
                        </el-select>
                    </div>

                    <div class="tuning-panel">
                        <div class="tuning-head">
                            <span>识别频率</span>
                            <span class="tuning-hint">{{ currentScanInterval.hint }}</span>
                        </div>
                        <el-select v-model="scanIntervalId" class="resolution-select" :disabled="startingCamera">
                            <el-option
                                v-for="item in SCAN_INTERVAL_PRESETS"
                                :key="item.id"
                                :label="item.label"
                                :value="item.id"
                            />
                        </el-select>
                    </div>

                    <div class="tuning-panel">
                        <div class="tuning-head">
                            <span>同人去重</span>
                            <span class="tuning-hint">开启后，窗口内同一人重复刷脸不新增记录</span>
                        </div>
                        <div class="dedup-row">
                            <el-switch v-model="dedupEnabled" active-text="开启" inactive-text="关闭" />
                            <el-select
                                v-model="dedupSeconds"
                                class="dedup-select"
                                :disabled="!dedupEnabled"
                            >
                                <el-option
                                    v-for="item in DEDUP_WINDOW_OPTIONS"
                                    :key="item.value"
                                    :label="item.label"
                                    :value="item.value"
                                />
                            </el-select>
                        </div>
                    </div>

                    <div class="tuning-panel">
                        <div class="tuning-head">
                            <span>识别阈值 {{ matchThreshold.toFixed(2) }}</span>
                            <span class="tuning-hint">越小越严格，越大越容易认成同一人</span>
                        </div>
                        <el-slider v-model="matchThreshold" :min="0.4" :max="0.8" :step="0.01" :show-tooltip="false" />
                    </div>

                    <div class="status-bar">
                        <span class="status-text">{{ statusText }}</span>
                        <span v-if="lastResult" class="last-result">
                            上次：{{ lastResult.user_id }}
                            <el-tag v-if="lastResult.is_new_person" size="small" type="success">新人</el-tag>
                            <el-tag v-else-if="lastResult.punch_skipped" size="small" type="info">已去重</el-tag>
                            <span v-if="lastResult.match_distance != null">
                                · 距离 {{ lastResult.match_distance.toFixed(3) }}
                            </span>
                            · {{ formatTime(lastResult.punched_at) }}
                        </span>
                    </div>

                    <div class="action-bar">
                        <el-button
                            type="primary"
                            :loading="startingCamera || modelsLoading"
                            @click="toggleCamera"
                        >
                            {{ cameraButtonText }}
                        </el-button>
                    </div>
                </el-card>
            </el-col>

            <el-col :xs="24" :lg="12">
                <el-card shadow="hover" class="history-card">
                    <template #header>
                        <div class="card-header">
                            <span class="page-title">打卡历史</span>
                            <el-button size="small" :loading="loading" @click="loadPunches">刷新</el-button>
                        </div>
                    </template>

                    <div class="history-toolbar">
                        <el-input
                            v-model="searchUserId"
                            placeholder="输入用户 ID 搜索，如 U0001"
                            clearable
                            @keyup.enter="handleSearch"
                            @clear="handleSearch"
                        />
                        <el-button type="primary" @click="handleSearch">搜索</el-button>
                    </div>

                    <el-table :data="punches" v-loading="loading" stripe size="small" max-height="420">
                        <el-table-column type="index" label="#" width="50" />
                        <el-table-column prop="user_id" label="用户 ID" width="100" />
                        <el-table-column label="打卡时间" min-width="160">
                            <template #default="{ row }">
                                {{ formatTime(row.punched_at) }}
                            </template>
                        </el-table-column>
                        <el-table-column label="操作" width="70" fixed="right">
                            <template #default="{ row }">
                                <el-button type="danger" link size="small" @click="handleDeletePunch(row)">
                                    删除
                                </el-button>
                            </template>
                        </el-table-column>
                    </el-table>

                    <div class="pager">
                        <el-pagination
                            v-model:current-page="page"
                            v-model:page-size="pageSize"
                            :total="total"
                            :page-sizes="[10, 20, 50]"
                            layout="total, sizes, prev, pager, next"
                            background
                            small
                            @current-change="loadPunches"
                            @size-change="handleSizeChange"
                        />
                    </div>
                </el-card>

                <el-card shadow="hover" class="persons-card mgt20">
                    <template #header>
                        <div class="card-header">
                            <span class="page-title">已登记人员</span>
                            <div class="card-header-actions">
                                <el-tag size="small" type="info">{{ persons.length }} 人</el-tag>
                                <el-button size="small" :loading="personsLoading" @click="loadPersons">刷新</el-button>
                            </div>
                        </div>
                    </template>

                    <div class="history-toolbar">
                        <el-input
                            v-model="searchPersonUserId"
                            placeholder="输入用户 ID 搜索，如 U0001"
                            clearable
                            @keyup.enter="handlePersonSearch"
                            @clear="handlePersonSearch"
                        />
                        <el-button type="primary" @click="handlePersonSearch">搜索</el-button>
                    </div>

                    <el-table :data="persons" v-loading="personsLoading" stripe size="small" max-height="280">
                        <el-table-column label="人员" min-width="168">
                            <template #default="{ row }">
                                <div
                                    class="person-cell"
                                    :class="{ clickable: row.has_reference_image }"
                                    @click="openPersonPhoto(row)"
                                >
                                    <div class="person-avatar" :class="{ placeholder: !row.has_reference_image }">
                                        <el-image
                                            v-if="row.has_reference_image"
                                            :src="getPersonPhotoUrl(row.user_id)"
                                            fit="cover"
                                            class="person-photo"
                                            loading="lazy"
                                        />
                                        <span v-else>?</span>
                                    </div>
                                    <div class="person-meta">
                                        <span class="person-id">{{ row.user_id }}</span>
                                        <span class="person-tip">
                                            {{ row.has_reference_image ? '点击查看标准照' : '未采集标准照' }}
                                        </span>
                                    </div>
                                </div>
                            </template>
                        </el-table-column>
                        <el-table-column prop="punch_count" label="打卡次数" width="88" align="right" />
                        <el-table-column label="登记时间" min-width="140">
                            <template #default="{ row }">
                                {{ formatTime(row.created_at) }}
                            </template>
                        </el-table-column>
                        <el-table-column label="操作" width="70" fixed="right">
                            <template #default="{ row }">
                                <el-button type="danger" link size="small" @click="handleDeletePerson(row)">
                                    删除
                                </el-button>
                            </template>
                        </el-table-column>
                    </el-table>
                </el-card>
            </el-col>
        </el-row>

        <el-image-viewer
            v-if="photoPreviewVisible"
            :url-list="[photoPreviewUrl]"
            @close="photoPreviewVisible = false"
        />
    </div>
</template>

<script setup lang="ts" name="demo-attendance">
import { computed, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
    attendancePunch,
    deleteAttendancePerson,
    deleteAttendancePunch,
    getAttendancePersonPhotoUrl,
    listAttendancePersons,
    listAttendancePunches,
} from '@/api';

type FaceApiModule = typeof import('@vladmandic/face-api');
type FaceDetectionResult = {
    descriptor: Float32Array;
    detection: {
        box: { x: number; y: number; width: number; height: number };
        score: number;
    };
};

interface PunchItem {
    id: number;
    user_id: string;
    punched_at: string;
}

interface PersonItem {
    id: number;
    user_id: string;
    created_at: string;
    punch_count: number;
    has_reference_image: boolean;
}

interface PunchResult {
    user_id: string;
    punched_at: string;
    is_new_person: boolean;
    match_distance: number | null;
    reference_image_updated: boolean;
    punch_skipped?: boolean;
}

interface ScanIntervalPreset {
    id: string;
    label: string;
    intervalMs: number;
    hint: string;
}

interface DedupWindowOption {
    label: string;
    value: number;
}

interface ResolutionPreset {
    id: string;
    label: string;
    width: number;
    height: number;
    hint: string;
    detectInputSize: number;
    detectIntervalMs: number;
}

const RESOLUTION_PRESETS: ResolutionPreset[] = [
    {
        id: '360p',
        label: '480×360（流畅）',
        width: 480,
        height: 360,
        hint: '最流畅，画面较糊',
        detectInputSize: 224,
        detectIntervalMs: 350,
    },
    {
        id: '480p',
        label: '640×480（标清）',
        width: 640,
        height: 480,
        hint: '流畅与清晰度均衡',
        detectInputSize: 224,
        detectIntervalMs: 400,
    },
    {
        id: '720p',
        label: '1280×720（高清）',
        width: 1280,
        height: 720,
        hint: '推荐，画面清晰',
        detectInputSize: 320,
        detectIntervalMs: 450,
    },
    {
        id: '1080p',
        label: '1920×1080（超清）',
        width: 1920,
        height: 1080,
        hint: '最清晰，较耗性能',
        detectInputSize: 416,
        detectIntervalMs: 550,
    },
];

const SCAN_INTERVAL_PRESETS: ScanIntervalPreset[] = [
    { id: '2ps', label: '一秒刷 2 次', intervalMs: 500, hint: '最快，适合连续测试' },
    { id: '1ps', label: '一秒刷 1 次', intervalMs: 1000, hint: '默认，流畅与稳定均衡' },
    { id: '0.5ps', label: '两秒刷 1 次', intervalMs: 2000, hint: '最慢，减少重复提交' },
];

const DEDUP_WINDOW_OPTIONS: DedupWindowOption[] = [
    { label: '1 秒内去重', value: 1 },
    { label: '2 秒内去重', value: 2 },
    { label: '5 秒内去重', value: 5 },
];

const THRESHOLD_STORAGE_KEY = 'attendance_match_threshold';
const RESOLUTION_STORAGE_KEY = 'attendance_resolution_preset';
const SCAN_INTERVAL_STORAGE_KEY = 'attendance_scan_interval';
const DEDUP_ENABLED_STORAGE_KEY = 'attendance_dedup_enabled';
const DEDUP_SECONDS_STORAGE_KEY = 'attendance_dedup_seconds';
const MODEL_URL = '/models';
const STABLE_FRAMES = 2;

const videoRef = ref<HTMLVideoElement | null>(null);
const canvasRef = ref<HTMLCanvasElement | null>(null);
const modelsReady = ref(false);
const modelsLoading = ref(false);
const cameraOn = ref(false);
const startingCamera = ref(false);
const punching = ref(false);
const statusText = ref('正在加载列表…');
const lastResult = ref<PunchResult | null>(null);
const photoPreviewVisible = ref(false);
const photoPreviewUrl = ref('');
const matchThreshold = ref(Number(localStorage.getItem(THRESHOLD_STORAGE_KEY)) || 0.65);
const savedResolution = localStorage.getItem(RESOLUTION_STORAGE_KEY);
const resolutionPresetId = ref(
    RESOLUTION_PRESETS.some((item) => item.id === savedResolution) ? savedResolution! : '720p',
);
const savedScanInterval = localStorage.getItem(SCAN_INTERVAL_STORAGE_KEY);
const scanIntervalId = ref(
    SCAN_INTERVAL_PRESETS.some((item) => item.id === savedScanInterval) ? savedScanInterval! : '1ps',
);
const dedupEnabled = ref(localStorage.getItem(DEDUP_ENABLED_STORAGE_KEY) !== 'false');
const savedDedupSeconds = Number(localStorage.getItem(DEDUP_SECONDS_STORAGE_KEY));
const dedupSeconds = ref(
    DEDUP_WINDOW_OPTIONS.some((item) => item.value === savedDedupSeconds) ? savedDedupSeconds : 2,
);
const actualResolution = ref('');

const currentResolution = computed(
    () => RESOLUTION_PRESETS.find((item) => item.id === resolutionPresetId.value) ?? RESOLUTION_PRESETS[2],
);

const currentScanInterval = computed(
    () => SCAN_INTERVAL_PRESETS.find((item) => item.id === scanIntervalId.value) ?? SCAN_INTERVAL_PRESETS[1],
);

const scanIntervalMs = computed(() => currentScanInterval.value.intervalMs);

const cameraButtonText = computed(() => {
    if (cameraOn.value) return '关闭摄像头';
    if (modelsLoading.value) return '加载模型中…';
    return '打开摄像头';
});

let modelsLoadPromise: Promise<void> | null = null;

const punches = ref<PunchItem[]>([]);
const persons = ref<PersonItem[]>([]);
const loading = ref(false);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const searchUserId = ref('');
const searchPersonUserId = ref('');
const personsLoading = ref(false);
const photoVersion = ref<Record<string, number>>({});

let stream: MediaStream | null = null;
let rafId: number | null = null;
let stableCount = 0;
let lastPunchTime = 0;
let detecting = false;
let overlayReady = false;
let lastDetectTime = 0;
let faceapi: FaceApiModule | null = null;
let detectorOptions: { inputSize: number; scoreThreshold: number } | null = null;
let detectIntervalMs = currentResolution.value.detectIntervalMs;
let punchCooldownMs = scanIntervalMs.value;

watch(matchThreshold, (value) => {
    localStorage.setItem(THRESHOLD_STORAGE_KEY, String(value));
});

watch(scanIntervalId, () => {
    localStorage.setItem(SCAN_INTERVAL_STORAGE_KEY, scanIntervalId.value);
    punchCooldownMs = scanIntervalMs.value;
    detectIntervalMs = Math.min(currentResolution.value.detectIntervalMs, punchCooldownMs);
});

watch(dedupEnabled, (value) => {
    localStorage.setItem(DEDUP_ENABLED_STORAGE_KEY, String(value));
});

watch(dedupSeconds, (value) => {
    localStorage.setItem(DEDUP_SECONDS_STORAGE_KEY, String(value));
});

const applyResolutionPreset = () => {
    const preset = currentResolution.value;
    detectIntervalMs = Math.min(preset.detectIntervalMs, scanIntervalMs.value);
    if (faceapi) {
        detectorOptions = new faceapi.TinyFaceDetectorOptions({
            inputSize: preset.detectInputSize,
            scoreThreshold: 0.5,
        });
    }
};

watch(resolutionPresetId, () => {
    localStorage.setItem(RESOLUTION_STORAGE_KEY, resolutionPresetId.value);
    applyResolutionPreset();
});

const getFaceApi = async () => {
    if (!faceapi) {
        faceapi = await import('@vladmandic/face-api');
    }
    applyResolutionPreset();
    return faceapi;
};

const formatTime = (value: string) => {
    if (!value) return '-';
    const raw = value.trim();
    const hasTz = /[zZ]$|[+-]\d{2}:\d{2}$/.test(raw);
    const iso = hasTz ? raw : `${raw.replace(' ', 'T')}Z`;
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString('zh-CN', { hour12: false });
};

const getPersonPhotoUrl = (userId: string) => getAttendancePersonPhotoUrl(userId, photoVersion.value[userId] || 0);

const openPersonPhoto = (row: PersonItem) => {
    if (!row.has_reference_image) return;
    photoPreviewUrl.value = getPersonPhotoUrl(row.user_id);
    photoPreviewVisible.value = true;
};

const cropFaceImage = (video: HTMLVideoElement, detection: FaceDetectionResult) => {
    const box = detection.detection.box;
    const padX = box.width * 0.15;
    const padY = box.height * 0.15;
    const x = Math.max(0, Math.floor(box.x - padX));
    const y = Math.max(0, Math.floor(box.y - padY));
    const width = Math.min(video.videoWidth - x, Math.floor(box.width + padX * 2));
    const height = Math.min(video.videoHeight - y, Math.floor(box.height + padY * 2));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(width, 1);
    canvas.height = Math.max(height, 1);
    const ctx = canvas.getContext('2d');
    ctx?.drawImage(video, x, y, width, height, 0, 0, canvas.width, canvas.height);
    return {
        face_image: canvas.toDataURL('image/jpeg', 0.85),
        face_score: detection.detection.score * canvas.width * canvas.height,
    };
};

const waitVideoReady = (video: HTMLVideoElement) =>
    new Promise<void>((resolve) => {
        if (video.readyState >= 1 && video.videoWidth > 0) {
            resolve();
            return;
        }
        video.onloadedmetadata = () => resolve();
    });

const loadModels = async () => {
    const api = await getFaceApi();
    await Promise.all([
        api.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
        api.nets.faceLandmark68TinyNet.loadFromUri(MODEL_URL),
        api.nets.faceRecognitionNet.loadFromUri(MODEL_URL),
    ]);
    modelsReady.value = true;
    if (!cameraOn.value) {
        statusText.value = '模型已就绪';
    }
};

const ensureModels = async () => {
    if (modelsReady.value) return;
    if (!modelsLoadPromise) {
        modelsLoading.value = true;
        statusText.value = '正在加载识别模型…';
        modelsLoadPromise = loadModels()
            .catch(() => {
                modelsLoadPromise = null;
                statusText.value = '模型加载失败，请确认 /public/models 下模型文件齐全';
                ElMessage.error('人脸识别模型加载失败');
                throw new Error('models load failed');
            })
            .finally(() => {
                modelsLoading.value = false;
            });
    }
    await modelsLoadPromise;
};

const loadPunches = async () => {
    loading.value = true;
    try {
        const params: { page: number; page_size: number; user_id?: string } = {
            page: page.value,
            page_size: pageSize.value,
        };
        const keyword = searchUserId.value.trim();
        if (keyword) {
            params.user_id = keyword;
        }
        const res = await listAttendancePunches(params);
        punches.value = res.data.items;
        total.value = res.data.total;
    } catch {
        ElMessage.error('加载打卡历史失败');
    } finally {
        loading.value = false;
    }
};

const handleSearch = () => {
    page.value = 1;
    loadPunches();
};

const loadPersons = async () => {
    personsLoading.value = true;
    try {
        const keyword = searchPersonUserId.value.trim();
        const res = await listAttendancePersons(keyword ? { user_id: keyword } : undefined);
        persons.value = res.data;
    } catch {
        ElMessage.error('加载人员列表失败');
    } finally {
        personsLoading.value = false;
    }
};

const handlePersonSearch = () => {
    loadPersons();
};

const handleSizeChange = () => {
    page.value = 1;
    loadPunches();
};

const handleDeletePunch = async (row: PunchItem) => {
    try {
        await ElMessageBox.confirm(
            `确定删除 ${row.user_id} 在 ${formatTime(row.punched_at)} 的打卡记录？`,
            '删除确认',
            { type: 'warning' },
        );
        await deleteAttendancePunch(row.id);
        ElMessage.success('已删除打卡记录');
        await loadPunches();
        await loadPersons();
    } catch {
        // 用户取消或请求失败
    }
};

const handleDeletePerson = async (row: PersonItem) => {
    try {
        await ElMessageBox.confirm(
            `确定删除人员 ${row.user_id}？将同时删除其 ${row.punch_count} 条打卡记录。`,
            '删除确认',
            { type: 'warning' },
        );
        await deleteAttendancePerson(row.id);
        ElMessage.success('已删除人员');
        await Promise.all([loadPunches(), loadPersons()]);
    } catch {
        // 用户取消或请求失败
    }
};

const stopCamera = () => {
    if (rafId !== null) {
        cancelAnimationFrame(rafId);
        rafId = null;
    }
    if (stream) {
        stream.getTracks().forEach((track) => track.stop());
        stream = null;
    }
    if (videoRef.value) {
        videoRef.value.srcObject = null;
    }
    cameraOn.value = false;
    overlayReady = false;
    actualResolution.value = '';
    stableCount = 0;
    detecting = false;
    statusText.value = modelsReady.value ? '摄像头已关闭' : statusText.value;
};

const ensureOverlaySize = (video: HTMLVideoElement) => {
    const canvas = canvasRef.value;
    if (!canvas || !faceapi || overlayReady || video.videoWidth <= 0) return;
    faceapi.matchDimensions(canvas, { width: video.videoWidth, height: video.videoHeight });
    overlayReady = true;
};

const drawOverlay = (video: HTMLVideoElement, detection: FaceDetectionResult | undefined) => {
    const canvas = canvasRef.value;
    if (!canvas || !faceapi || !detection) return;

    const ctx = canvas.getContext('2d');
    ctx?.clearRect(0, 0, canvas.width, canvas.height);
    const resized = faceapi.resizeResults(detection, { width: video.videoWidth, height: video.videoHeight });
    faceapi.draw.drawDetections(canvas, resized);
    faceapi.draw.drawFaceLandmarks(canvas, resized);
};

const formatCooldownHint = (ms: number) => {
    if (ms >= 1000) {
        const seconds = ms / 1000;
        return `请 ${seconds} 秒后再打卡`;
    }
    return `请 ${ms} 毫秒后再打卡`;
};

const submitPunch = async (detection: FaceDetectionResult) => {
    if (punching.value) return;
    if (Date.now() - lastPunchTime < punchCooldownMs) {
        statusText.value = formatCooldownHint(punchCooldownMs);
        return;
    }

    const video = videoRef.value;
    if (!video) return;

    punching.value = true;
    statusText.value = '正在提交打卡…';
    try {
        const { face_image, face_score } = cropFaceImage(video, detection);
        const res = await attendancePunch({
            descriptor: Array.from(detection.descriptor),
            match_threshold: matchThreshold.value,
            face_image,
            face_score,
            dedup_enabled: dedupEnabled.value,
            dedup_seconds: dedupSeconds.value,
        });
        const data = res.data as PunchResult;
        lastResult.value = data;
        lastPunchTime = Date.now();

        if (data.punch_skipped) {
            statusText.value = `已识别 ${data.user_id}，${dedupSeconds.value} 秒内重复刷脸已跳过`;
            return;
        }

        statusText.value = data.is_new_person
            ? `新人登记并打卡成功：${data.user_id}`
            : `打卡成功：${data.user_id}`;
        ElMessage.success(statusText.value);
        await loadPunches();
        if (data.is_new_person || data.reference_image_updated) {
            if (data.reference_image_updated) {
                photoVersion.value[data.user_id] = Date.now();
            }
            await loadPersons();
        } else {
            const person = persons.value.find((item) => item.user_id === data.user_id);
            if (person) {
                person.punch_count += 1;
            }
        }
    } catch (err: unknown) {
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        statusText.value = '打卡失败，请重试';
        ElMessage.error(typeof detail === 'string' ? detail : '打卡失败');
    } finally {
        punching.value = false;
    }
};

const detectLoop = async () => {
    if (!cameraOn.value) return;

    const video = videoRef.value;
    if (!video || video.readyState < 2 || punching.value || !faceapi || !detectorOptions) {
        rafId = requestAnimationFrame(() => {
            detectLoop().catch(() => {
                statusText.value = '人脸检测异常';
            });
        });
        return;
    }

    ensureOverlaySize(video);

    if (!detecting && Date.now() - lastDetectTime >= detectIntervalMs) {
        detecting = true;
        lastDetectTime = Date.now();
        try {
            const detection = await faceapi
                .detectSingleFace(video, detectorOptions)
                .withFaceLandmarks(true)
                .withFaceDescriptor() as FaceDetectionResult | undefined;

            if (detection) {
                drawOverlay(video, detection);
            } else {
                const canvas = canvasRef.value;
                canvas?.getContext('2d')?.clearRect(0, 0, canvas.width, canvas.height);
            }

            if (!detection) {
                stableCount = 0;
                if (!punching.value && Date.now() - lastPunchTime >= punchCooldownMs) {
                    statusText.value = '请将面部对准摄像头';
                }
            } else {
                stableCount += 1;
                if (stableCount < STABLE_FRAMES) {
                    statusText.value = `检测到人脸（${stableCount}/${STABLE_FRAMES}）…`;
                } else if (Date.now() - lastPunchTime >= punchCooldownMs) {
                    stableCount = 0;
                    await submitPunch(detection);
                } else {
                    statusText.value = formatCooldownHint(punchCooldownMs);
                }
            }
        } finally {
            detecting = false;
        }
    }

    rafId = requestAnimationFrame(() => {
        detectLoop().catch(() => {
            statusText.value = '人脸检测异常';
        });
    });
};

const openCameraStream = async () => {
    const preset = currentResolution.value;
    stream = await navigator.mediaDevices.getUserMedia({
        video: {
            facingMode: 'user',
            width: { ideal: preset.width },
            height: { ideal: preset.height },
        },
        audio: false,
    });
    const video = videoRef.value;
    if (!video) return;
    video.srcObject = stream;
    await waitVideoReady(video);
    await video.play();
    actualResolution.value = `${video.videoWidth}×${video.videoHeight}`;
};

const startCamera = async () => {
    if (cameraOn.value) return;
    await openCameraStream();
    cameraOn.value = true;
    overlayReady = false;
    statusText.value = '请将面部对准摄像头';
    rafId = requestAnimationFrame(() => {
        detectLoop().catch(() => {
            statusText.value = '人脸检测异常';
        });
    });
};

const handleResolutionChange = async () => {
    if (!cameraOn.value) return;
    startingCamera.value = true;
    try {
        if (rafId !== null) {
            cancelAnimationFrame(rafId);
            rafId = null;
        }
        if (stream) {
            stream.getTracks().forEach((track) => track.stop());
            stream = null;
        }
        overlayReady = false;
        stableCount = 0;
        await openCameraStream();
        rafId = requestAnimationFrame(() => {
            detectLoop().catch(() => {
                statusText.value = '人脸检测异常';
            });
        });
        ElMessage.success(`已切换为 ${currentResolution.value.label}`);
    } catch {
        ElMessage.error('切换分辨率失败，请换较低档位重试');
        stopCamera();
    } finally {
        startingCamera.value = false;
    }
};

const toggleCamera = async () => {
    if (cameraOn.value) {
        stopCamera();
        return;
    }
    startingCamera.value = true;
    try {
        await ensureModels();
        await startCamera();
    } catch {
        if (modelsReady.value) {
            ElMessage.error('无法打开摄像头，请检查浏览器权限或换较低分辨率');
            statusText.value = '摄像头打开失败';
        }
    } finally {
        startingCamera.value = false;
    }
};

onMounted(async () => {
    await Promise.all([loadPunches(), loadPersons()]);
    statusText.value = '列表已加载，点击打开摄像头开始打卡';
});

onDeactivated(() => {
    stopCamera();
});

onBeforeUnmount(() => {
    stopCamera();
});
</script>

<style scoped>
.attendance-page .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}

.attendance-page .page-title {
    font-size: 16px;
    font-weight: 600;
}

.attendance-page .page-subtitle {
    margin-top: 4px;
    font-size: 12px;
    color: #909399;
}

.video-wrap {
    position: relative;
    width: 100%;
    aspect-ratio: 4 / 3;
    background: #111;
    border-radius: 8px;
    overflow: hidden;
    transform: scaleX(-1);
}

.video {
    position: absolute;
    inset: 0;
    z-index: 1;
    width: 100%;
    height: 100%;
    object-fit: cover;
    background: #000;
}

.overlay {
    position: absolute;
    inset: 0;
    z-index: 2;
    width: 100%;
    height: 100%;
    object-fit: cover;
    pointer-events: none;
}

.video-mask {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px;
    color: #fff;
    background: rgba(0, 0, 0, 0.55);
    text-align: center;
}

.tuning-panel {
    margin-top: 12px;
    padding: 8px 4px 0;
}

.tuning-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
    font-size: 13px;
    color: #303133;
}

.tuning-hint {
    font-size: 12px;
    color: #909399;
}

.resolution-select {
    width: 100%;
}

.dedup-row {
    display: flex;
    align-items: center;
    gap: 12px;
}

.dedup-select {
    flex: 1;
    min-width: 0;
}

.card-header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
}

.status-bar {
    margin-top: 12px;
    min-height: 44px;
}

.status-text {
    display: block;
    font-size: 14px;
    color: #303133;
}

.last-result {
    display: block;
    margin-top: 4px;
    font-size: 12px;
    color: #909399;
}

.action-bar {
    margin-top: 12px;
}

.pager {
    display: flex;
    justify-content: flex-end;
    margin-top: 12px;
}

.history-toolbar {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
}

.mgt20 {
    margin-top: 20px;
}

.person-photo {
    width: 100%;
    height: 100%;
    border-radius: 6px;
}

.person-cell {
    display: flex;
    align-items: center;
    gap: 10px;
}

.person-cell.clickable {
    cursor: pointer;
}

.person-cell.clickable:hover .person-id {
    color: #409eff;
}

.person-avatar {
    flex-shrink: 0;
    width: 44px;
    height: 44px;
    border-radius: 6px;
    overflow: hidden;
    background: #f2f3f5;
}

.person-avatar.placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    color: #c0c4cc;
    font-size: 18px;
    font-weight: 600;
}

.person-meta {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
}

.person-id {
    font-size: 14px;
    font-weight: 600;
    color: #303133;
}

.person-tip {
    font-size: 12px;
    color: #909399;
}
</style>
