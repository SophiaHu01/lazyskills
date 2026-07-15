import React from 'react';
import {Composition} from 'remotion';
import type {VidMotionProps} from './types';
import {VidMotion} from './VidMotion';

const FPS = 30;

export const Root: React.FC = () => {
  return (
    <Composition
      id="VidMotion"
      component={VidMotion}
      width={1080}
      height={1920}
      fps={FPS}
      durationInFrames={60 * FPS}
      defaultProps={{events: [], durationSec: 60, width: 1080, height: 1920} as VidMotionProps}
      calculateMetadata={({props}) => ({
        durationInFrames: Math.max(1, Math.round(props.durationSec * FPS)),
        width: props.width ?? 1080,   // 画布跟素材走,不写死竖屏
        height: props.height ?? 1920,
      })}
    />
  );
};
