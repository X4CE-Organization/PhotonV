/**
 * 直播用的 WebRTC 封装：
 *  - WHIP：浏览器直接推流（网页开播），不需要装 OBS
 *  - WHEP：浏览器直接拉流，延迟通常在 1 秒以内
 *
 * 两者都是「一次 HTTP 交换 SDP」的协议：
 *   1. 本地 createOffer / setLocalDescription
 *   2. POST 到对端地址，把 offer 发过去
 *   3. 把返回的 answer setRemoteDescription
 *   4. 结束时 DELETE 掉 Location 里返回的资源地址
 */

export interface WhipHandle {
  pc: RTCPeerConnection;
  resourceUrl: string;
}

export interface WhepHandle {
  pc: RTCPeerConnection;
  stop: () => void;
}

export interface LiveStats {
  bitrate: number;
  fps: number;
  width: number;
  height: number;
  packetsLost: number;
}

function iceConfig(): RTCConfiguration {
  return { iceServers: [] };
}

async function postSdp(url: string, offer: RTCSessionDescriptionInit): Promise<Response> {
  return fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/sdp' },
    body: offer.sdp,
  });
}

function waitIce(pc: RTCPeerConnection, timeoutMs = 3000): Promise<void> {
  if (pc.iceGatheringState === 'complete') return Promise.resolve();
  return new Promise((resolve) => {
    const done = () => {
      pc.removeEventListener('icegatheringstatechange', check);
      resolve();
    };
    const check = () => {
      if (pc.iceGatheringState === 'complete') done();
    };
    pc.addEventListener('icegatheringstatechange', check);
    // 不等完整收集，候选够了就先发，避免卡住
    setTimeout(done, timeoutMs);
  });
}

/** 开始推流（WHIP）。stream 一般是屏幕共享或摄像头 + 麦克风。 */
export async function startWhip(
  url: string,
  stream: MediaStream,
  onState?: (state: RTCPeerConnectionState) => void,
): Promise<WhipHandle> {
  const pc = new RTCPeerConnection(iceConfig());
  onState?.('connecting');
  pc.addEventListener('connectionstatechange', () => onState?.(pc.connectionState));
  stream.getTracks().forEach((track) => pc.addTrack(track, stream));

  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
  await waitIce(pc);

  const response = await postSdp(url, { type: 'offer', sdp: pc.localDescription?.sdp || offer.sdp });
  if (!response.ok) {
    pc.close();
    const detail = await response.text().catch(() => '');
    throw new Error(
      response.status === 404
        ? '推流地址不存在，请检查后台「直播」设置里的 WHIP 地址'
        : `推流被拒绝（${response.status}）${detail ? `：${detail.slice(0, 120)}` : ''}`,
    );
  }
  const answer = await response.text();
  await pc.setRemoteDescription({ type: 'answer', sdp: answer });

  const location = response.headers.get('Location') || '';
  const resourceUrl = location ? new URL(location, url).toString() : '';
  return { pc, resourceUrl };
}

/** 结束推流：按 WHIP 协议 DELETE 掉会话，然后关掉 PeerConnection。 */
export async function stopWhip(handle: WhipHandle | null): Promise<void> {
  if (!handle) return;
  try {
    if (handle.resourceUrl) await fetch(handle.resourceUrl, { method: 'DELETE' });
  } catch {
    /* 资源可能已经过期，忽略 */
  }
  try {
    handle.pc.close();
  } catch {
    /* ignore */
  }
}

/** 开始播放（WHEP），把远端画面挂到 video 元素上。 */
export async function startWhep(
  url: string,
  video: HTMLVideoElement,
  onState?: (state: RTCPeerConnectionState) => void,
): Promise<WhepHandle> {
  const pc = new RTCPeerConnection(iceConfig());
  onState?.('connecting');
  pc.addEventListener('connectionstatechange', () => onState?.(pc.connectionState));

  const remote = new MediaStream();
  pc.addEventListener('track', (event) => {
    remote.addTrack(event.track);
    if (video.srcObject !== remote) video.srcObject = remote;
    void video.play().catch(() => undefined);
  });
  // 约定只收视频和音频，方便服务端只发这两路
  pc.addTransceiver('video', { direction: 'recvonly' });
  pc.addTransceiver('audio', { direction: 'recvonly' });

  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
  await waitIce(pc);

  const response = await postSdp(url, { type: 'offer', sdp: pc.localDescription?.sdp || offer.sdp });
  if (!response.ok) {
    pc.close();
    throw new Error(`拉流失败（${response.status}）`);
  }
  const answer = await response.text();
  await pc.setRemoteDescription({ type: 'answer', sdp: answer });

  return {
    pc,
    stop: () => {
      try {
        video.srcObject = null;
      } catch {
        /* ignore */
      }
      try {
        pc.close();
      } catch {
        /* ignore */
      }
    },
  };
}

/** 采样一次推流统计（码率 / 帧率 / 分辨率）。 */
export async function sampleStats(pc: RTCPeerConnection): Promise<LiveStats | null> {
  try {
    const report = await pc.getStats();
    let result: LiveStats = { bitrate: 0, fps: 0, width: 0, height: 0, packetsLost: 0 };
    report.forEach((item: any) => {
      if (item.type === 'outbound-rtp' && item.kind === 'video') {
        result.bitrate = Number(item.bytesSent || 0);
        result.fps = Number(item.framesPerSecond || 0);
        result.width = Number(item.frameWidth || 0);
        result.height = Number(item.frameHeight || 0);
      }
      if (item.type === 'remote-inbound-rtp' && item.kind === 'video') {
        result.packetsLost = Number(item.packetsLost || 0);
      }
    });
    return result;
  } catch {
    return null;
  }
}

/** 浏览器能不能采集屏幕（需要 https 或 localhost）。 */
export function captureSupported(): boolean {
  const secure = window.isSecureContext || location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  return Boolean(secure && navigator.mediaDevices?.getUserMedia);
}

export function screenShareSupported(): boolean {
  return captureSupported() && Boolean((navigator.mediaDevices as any)?.getDisplayMedia);
}
