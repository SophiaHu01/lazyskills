import React from 'react';
import {AbsoluteFill, spring, useVideoConfig} from 'remotion';
import {SAFE_WIDTH, tokens} from '../tokens';
import type {StepsTimelineProps} from '../types';
import {useEventTiming} from './timing';

// 步骤时间线:讲流程/步骤时的纵向步骤线,逐步点亮(每步间隔 12 帧),active 步高亮。

type Props = {
  event: {start: number; hold: number; props: StepsTimelineProps};
};

const STEP_STAGGER_F = 12;
const DOT = 30;

export const StepsTimeline: React.FC<Props> = ({event}) => {
  const {steps, active} = event.props;
  const {local, visible, enter, opacity} = useEventTiming(event.start, event.hold);
  const {fps} = useVideoConfig();
  if (!visible || steps.length === 0) return null;
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
      <div
        style={{
          marginBottom: 380,
          background: tokens.paper,
          borderRadius: 28,
          padding: '44px 56px',
          boxShadow: '0 14px 44px rgba(38,32,25,0.35)',
          borderBottom: `8px solid ${tokens.accent}`,
          maxWidth: SAFE_WIDTH,
          boxSizing: 'border-box',
          opacity,
          transform: `translateY(${(1 - enter) * -46}px) scale(${0.94 + 0.06 * enter})`,
        }}
      >
        {steps.map((step, i) => {
          const lit = spring({
            frame: Math.max(0, local - 8 - i * STEP_STAGGER_F),
            fps,
            config: {damping: 13, stiffness: 170},
            durationInFrames: 16,
          });
          const isActive = active === i;
          const dotColor = isActive ? tokens.highlight : tokens.accent;
          const isLast = i === steps.length - 1;
          return (
            <div key={i} style={{display: 'flex', alignItems: 'stretch'}}>
              {/* 左轨:圆点 + 连线 */}
              <div
                style={{
                  width: DOT,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  marginRight: 26,
                  flexShrink: 0,
                }}
              >
                <div
                  style={{
                    width: DOT,
                    height: DOT,
                    borderRadius: '50%',
                    marginTop: 8,
                    background: dotColor,
                    border: `4px solid ${tokens.ink}`,
                    boxSizing: 'border-box',
                    opacity: 0.25 + 0.75 * lit,
                    transform: `scale(${0.6 + 0.4 * lit})`,
                    flexShrink: 0,
                  }}
                />
                {!isLast ? (
                  <div
                    style={{
                      width: 5,
                      flex: 1,
                      marginTop: 4,
                      marginBottom: 4,
                      borderRadius: 3,
                      background: tokens.ink,
                      opacity: 0.18,
                    }}
                  />
                ) : null}
              </div>
              <div
                style={{
                  fontFamily: tokens.font,
                  fontWeight: isActive ? 800 : 600,
                  fontSize: 40,
                  lineHeight: 1.3,
                  color: isActive ? tokens.accent : tokens.ink,
                  paddingBottom: isLast ? 0 : 34,
                  opacity: 0.3 + 0.7 * lit,
                  transform: `translateX(${(1 - lit) * 24}px)`,
                }}
              >
                {step}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
