import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

// 所有组件共用的出入场节拍(沿 VidCaption CardLayer 的惯例):
// spring 进场 18 帧,hold 结束后 10 帧淡出,hold+12 帧后彻底不渲。
export const EXIT_FADE_F = 10;
export const EXIT_WINDOW_F = 12;

export type EventTiming = {
  /** 相对事件起点的本地帧号 */
  local: number;
  /** hold 换算成的帧数 */
  holdF: number;
  /** 是否在可见窗口内(窗口外组件应 return null) */
  visible: boolean;
  /** spring 进场进度 0→1(带弹性) */
  enter: number;
  /** 淡出进度 1→0 */
  exit: number;
  /** min(enter, exit),直接当容器 opacity 用 */
  opacity: number;
  fps: number;
};

export function useEventTiming(start: number, hold: number): EventTiming {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const local = frame - Math.round(start * fps);
  const holdF = Math.round(hold * fps);
  const visible = local >= 0 && local <= holdF + EXIT_WINDOW_F;
  const enter = spring({
    frame: Math.max(local, 0),
    fps,
    config: {damping: 14, stiffness: 160},
    durationInFrames: 18,
  });
  const exit = interpolate(local, [holdF, holdF + EXIT_FADE_F], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return {local, holdF, visible, enter, exit, opacity: Math.min(enter, exit), fps};
}
