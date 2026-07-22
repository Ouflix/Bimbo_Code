'''
Aceasta este versiunea 2.0 a scriptului de detectie a pozitiei corpului (folosit pentru validarea exercitiilor executate de catre pacient). Initial folosisem o camera generica de raspberry pi ,dar
la sosirea camerei Luxonis Oak D Lite am lucrat la implementarea acestei versiuni ce se foloseste de DepthAi V3. Codul a fost facut integral de catre mine fiind testat pe doua exercitii (flexie umar si 
abductie umar)
'''

import time
import depthai as dai
import cv2
import numpy as np
import mediapipe as mp
from collections import deque


def _angle_3d(a, b, c):
    if a is None or b is None or c is None:
        return None
    ba = a - b
    bc = c - b
    nba = np.linalg.norm(ba)
    nbc = np.linalg.norm(bc)
    if nba < 1e-6 or nbc < 1e-6:
        return None
    cosv = np.dot(ba, bc) / (nba * nbc)
    cosv = np.clip(cosv, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosv)))


def _deproject(u, v, z, fx, fy, cx, cy):
    x = (u - cx) * z / fx
    y = (v - cy) * z / fy
    return np.array([x, y, z], dtype=np.float32)


def _sample_depth(depth_frame, u, v, win=4):
    h, w = depth_frame.shape
    u0, u1 = max(0, u - win), min(w, u + win + 1)
    v0, v1 = max(0, v - win), min(h, v + win + 1)
    patch = depth_frame[v0:v1, u0:u1]
    valid = patch[patch > 0]
    if valid.size == 0:
        return None
    return float(np.median(valid)) / 1000.0


class TrajectoryValidator:
    def __init__(self, neutral_range, target_range, increasing,
                 min_frames=5, max_frames=240, max_jump=45, monotonic_ratio=0.5):
        self.neutral_range = neutral_range
        self.target_range = target_range
        self.increasing = increasing
        self.min_frames = min_frames
        self.max_frames = max_frames
        self.max_jump = max_jump
        self.monotonic_ratio = monotonic_ratio
        self.reset()

    def reset(self):
        self.state = "WAIT_NEUTRAL"
        self.history = deque(maxlen=300)
        self.frames_in_motion = 0

    def _in(self, angle, rng):
        return rng[0] <= angle <= rng[1]

    def _smooth_and_monotonic(self):
        if len(self.history) < 3:
            return True
        diffs = np.diff(list(self.history))
        if np.max(np.abs(diffs)) > self.max_jump:
            return False
        good = np.sum(diffs > 0) if self.increasing else np.sum(diffs < 0)
        return good / len(diffs) >= self.monotonic_ratio

    def update(self, angle):
        if angle is None:
            return "TRACKING_LOST"

        if self.state == "WAIT_NEUTRAL":
            if self._in(angle, self.neutral_range):
                self.state = "READY"
            return "WAIT_NEUTRAL"

        if self.state == "READY":
            if not self._in(angle, self.neutral_range):
                self.state = "IN_MOTION"
                self.frames_in_motion = 0
                self.history.clear()
                self.history.append(angle)
            return "READY"

        if self.state == "IN_MOTION":
            self.frames_in_motion += 1
            self.history.append(angle)

            if self.frames_in_motion > self.max_frames:
                self.reset()
                return "TOO_SLOW"

            if self._in(angle, self.target_range):
                if self.frames_in_motion < self.min_frames:
                    self.reset()
                    return "TOO_FAST"
                if not self._smooth_and_monotonic():
                    self.reset()
                    return "NOT_SMOOTH"
                self.state = "DONE"
                return "VALID_REP"
            return "IN_MOTION"

        return "DONE"

    def progress(self, angle):
        if angle is None:
            return 0.0
        n_mid = sum(self.neutral_range) / 2
        t_mid = sum(self.target_range) / 2
        if t_mid == n_mid:
            return 0.0
        p = (angle - n_mid) / (t_mid - n_mid)
        return float(np.clip(p, 0.0, 1.0))


class LivenessChecker:
    def __init__(self, window=30, min_live_joints=2,
                 var_min=1e-8, var_max=0.5, min_depth_spread=0.02):
        self.window = window
        self.min_live_joints = min_live_joints
        self.var_min = var_min
        self.var_max = var_max
        self.min_depth_spread = min_depth_spread
        self.z_hist = {}

    def push(self, joint_idx, z):
        if z is None:
            return
        if joint_idx not in self.z_hist:
            self.z_hist[joint_idx] = deque(maxlen=self.window)
        self.z_hist[joint_idx].append(z)

    def check(self, current_pts):
        live_joints = 0
        for zs in self.z_hist.values():
            if len(zs) < self.window // 2:
                continue
            var = float(np.var(list(zs)))
            if self.var_min < var < self.var_max:
                live_joints += 1

        zs_now = [p[2] for p in current_pts.values() if p is not None]
        spread_ok = False
        if len(zs_now) >= 4:
            spread_ok = (max(zs_now) - min(zs_now)) > self.min_depth_spread

        temporal_ok = live_joints >= self.min_live_joints
        return temporal_ok and spread_ok, live_joints


def _build_pipeline(device, w=640, h=480, fps=20):
    pipeline = dai.Pipeline(device)

    cam_rgb = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_A)
    mono_l = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_B)
    mono_r = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_C)

    rgb_out = cam_rgb.requestOutput(
        size=(w, h),
        type=dai.ImgFrame.Type.RGB888i,
        resizeMode=dai.ImgResizeMode.CROP,
        fps=fps,
    )
    mono_l_out = mono_l.requestOutput(size=(w, h), fps=fps)
    mono_r_out = mono_r.requestOutput(size=(w, h), fps=fps)

    stereo = pipeline.create(dai.node.StereoDepth)
    stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.FAST_ACCURACY)
    stereo.setLeftRightCheck(True)
    stereo.setSubpixel(False)
    stereo.setExtendedDisparity(False)
    stereo.setDepthAlign(dai.CameraBoardSocket.CAM_A)
    stereo.setOutputSize(640, 480)
    mono_l_out.link(stereo.left)
    mono_r_out.link(stereo.right)

    sync = pipeline.create(dai.node.Sync)
    rgb_out.link(sync.inputs["rgb"])
    stereo.depth.link(sync.inputs["depth"])

    out_q = sync.out.createOutputQueue()
    return pipeline, out_q


EXERCISES = {
    0: {
        "name": "ARMS_HORIZONTAL_90",
        "success_msg": "Bravo! Ai ridicat corect bratele la orizontala",
        "shoulder_range": (60, 120),
        "elbow_range": (135, 181),
        "traj_joint": "shoulder",
        "traj_neutral": (0, 45),
        "traj_target": (60, 120),
        "traj_increasing": True,
    },
    1: {
        "name": "CACTUS_POSE",
        "success_msg": "Felicitari! Ai flexat foarte bine coatele, tine-o tot asa!",
        "shoulder_range": (65, 125),
        "elbow_range": (55, 125),
        "traj_joint": "elbow",
        "traj_neutral": (130, 181),
        "traj_target": (55, 125),
        "traj_increasing": False,
    },
}


def _draw_banner(img, text, color):
    h, w = img.shape[:2]
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.4, 4)
    by0 = h // 2 - th - 30
    by1 = h // 2 + th + 30
    overlay = img.copy()
    cv2.rectangle(overlay, (0, by0), (w, by1), color, -1)
    cv2.addWeighted(overlay, 0.45, img, 0.55, 0, img)
    tx = (w - tw) // 2
    ty = h // 2 + th // 2
    cv2.putText(img, text, (tx, ty),
                cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 4)


def pose_detect(index, strict=True):
    if index not in EXERCISES:
        raise ValueError(f"index necunoscut: {index}")
    cfg = EXERCISES[index]

    mp_pose = mp.solutions.pose
    mp_draw = mp.solutions.drawing_utils
    pose = mp_pose.Pose(min_detection_confidence=0.6, min_tracking_confidence=0.6)
    L = mp_pose.PoseLandmark

    stable_buffer = deque(maxlen=8)

    traj = TrajectoryValidator(
        neutral_range=cfg["traj_neutral"],
        target_range=cfg["traj_target"],
        increasing=cfg["traj_increasing"],
    )
    liveness = LivenessChecker()

    BANNER_SEC = 1.2
    banner_text = None
    banner_color = (0, 0, 0)
    banner_until = 0.0

    REJECT_MSG = {
        "TOO_FAST": "Incearca din nou - mai lent",
        "TOO_SLOW": "Incearca din nou",
        "NOT_SMOOTH": "Incearca din nou - miscare lina",
        "NOT_LIVE": "Incearca din nou",
    }

    wanted = [L.LEFT_SHOULDER, L.RIGHT_SHOULDER, L.LEFT_ELBOW, L.RIGHT_ELBOW,
              L.LEFT_WRIST, L.RIGHT_WRIST, L.LEFT_HIP, L.RIGHT_HIP]

    target_hold_frames = 0
    HOLD_NEEDED = 15
    traj_done = False

    def pose_state(pts):
        if any(pts.get(i.value) is None for i in wanted):
            return "LOW_VISIBILITY", None, None

        l_sh = _angle_3d(pts[L.LEFT_HIP.value],  pts[L.LEFT_SHOULDER.value],  pts[L.LEFT_ELBOW.value])
        r_sh = _angle_3d(pts[L.RIGHT_HIP.value], pts[L.RIGHT_SHOULDER.value], pts[L.RIGHT_ELBOW.value])
        l_el = _angle_3d(pts[L.LEFT_SHOULDER.value],  pts[L.LEFT_ELBOW.value],  pts[L.LEFT_WRIST.value])
        r_el = _angle_3d(pts[L.RIGHT_SHOULDER.value], pts[L.RIGHT_ELBOW.value], pts[L.RIGHT_WRIST.value])

        if None in (l_sh, r_sh, l_el, r_el):
            return "LOW_VISIBILITY", None, None

        sr, er = cfg["shoulder_range"], cfg["elbow_range"]
        in_target = (sr[0] < l_sh < sr[1] and sr[0] < r_sh < sr[1] and
                     er[0] < l_el < er[1] and er[0] < r_el < er[1])

        if cfg["traj_joint"] == "shoulder":
            traj_ang = (l_sh + r_sh) / 2.0
        else:
            traj_ang = (l_el + r_el) / 2.0

        return ("IN_TARGET" if in_target else "NEUTRAL"), traj_ang, (l_sh, l_el)

    with dai.Device() as device:
        print(device.getUsbSpeed())
        pipeline, out_q = _build_pipeline(device)

        calib = device.readCalibration()
        K = np.array(calib.getCameraIntrinsics(dai.CameraBoardSocket.CAM_A, 640, 480))
        fx, fy = K[0, 0], K[1, 1]
        cx, cy = K[0, 2], K[1, 2]

        pipeline.start()
        try:
            while pipeline.isRunning():
                msg = out_q.get()
                in_rgb = msg["rgb"]
                in_depth = msg["depth"]
                frame = in_rgb.getCvFrame()
                depth = in_depth.getFrame()

                results = pose.process(frame)
                bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                h, w = depth.shape

                overlay_lines = []

                if results.pose_landmarks:
                    mp_draw.draw_landmarks(bgr, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                    lm = results.pose_landmarks.landmark

                    pts = {}
                    for idx in wanted:
                        p = lm[idx.value]
                        if p.visibility < 0.5:
                            pts[idx.value] = None
                            continue
                        u = int(round(p.x * w))
                        v = int(round(p.y * h))
                        if not (0 <= u < w and 0 <= v < h):
                            pts[idx.value] = None
                            continue
                        z = _sample_depth(depth, u, v)
                        pts[idx.value] = _deproject(u, v, z, fx, fy, cx, cy) if z else None
                        liveness.push(idx.value, z)

                    state, traj_ang, dbg = pose_state(pts)
                    stable_buffer.append(state)
                    stable_state = max(set(stable_buffer), key=stable_buffer.count)

                    traj_result = traj.update(traj_ang)
                    live_ok, live_joints = liveness.check(pts)

                    success = False
                    if strict:
                        if traj_result == "VALID_REP":
                            traj_done = True
                        success = (traj_done and
                                   stable_state == "IN_TARGET" and live_ok)
                    else:
                        if stable_state == "IN_TARGET":
                            target_hold_frames += 1
                        else:
                            target_hold_frames = 0
                        success = target_hold_frames >= HOLD_NEEDED

                    if success:
                        print(f"{cfg['name']} DETECTED"
                              f"{' (strict)' if strict else ' (mod usor)'}")
                        print(f"[TTS] {cfg['success_msg']}")
                        _draw_banner(bgr, "BINE EXECUTAT", (0, 150, 0))
                        cv2.imshow('Pose Detection 3D', bgr)
                        cv2.waitKey(int(BANNER_SEC * 1000))
                        break

                    if strict and traj_result == "VALID_REP" and not live_ok:
                        print("[ANTI-CHEAT] repetare respinsa: NOT_LIVE")
                        banner_text = REJECT_MSG["NOT_LIVE"]
                        banner_color = (0, 90, 200)
                        banner_until = time.time() + BANNER_SEC
                    elif strict and traj_result in ("TOO_FAST", "TOO_SLOW", "NOT_SMOOTH"):
                        print(f"[ANTI-CHEAT] repetare respinsa: {traj_result}")
                        banner_text = REJECT_MSG.get(traj_result, "Incearca din nou")
                        banner_color = (0, 90, 200)
                        banner_until = time.time() + BANNER_SEC

                    col_state = (0, 255, 0) if stable_state == "IN_TARGET" else (255, 255, 255)
                    overlay_lines.append((stable_state, col_state))
                    if traj_ang is not None:
                        overlay_lines.append((f"traj: {traj_result}  ({cfg['traj_joint']}={traj_ang:.0f})",
                                              (255, 255, 0)))
                    overlay_lines.append((f"live_joints: {live_joints}  live_ok: {live_ok}  done: {traj_done}",
                                          (255, 200, 0)))
                    if dbg is not None:
                        overlay_lines.append((f"Shoulder3D: {dbg[0]:.0f}  Elbow3D: {dbg[1]:.0f}",
                                              (200, 200, 0)))

                    prog = traj.progress(traj_ang)
                    bx, by, bw, bh = 10, 170, 300, 22
                    cv2.rectangle(bgr, (bx, by), (bx + bw, by + bh), (80, 80, 80), 1)
                    cv2.rectangle(bgr, (bx, by), (bx + int(bw * prog), by + bh),
                                  (0, 200, 0), -1)
                else:
                    overlay_lines.append(("NO PERSON", (0, 0, 255)))

                y = 40
                for text, col in overlay_lines:
                    scale = 1.0 if y == 40 else 0.6
                    thick = 3 if y == 40 else 2
                    cv2.putText(bgr, text, (10, y),
                                cv2.FONT_HERSHEY_SIMPLEX, scale, col, thick)
                    y += 32

                if banner_text is not None and time.time() < banner_until:
                    _draw_banner(bgr, banner_text, banner_color)
                elif time.time() >= banner_until:
                    banner_text = None

                cv2.imshow('Pose Detection 3D', bgr)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            pipeline.stop()
            pose.close()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    pose_detect(0, False)
