function redactUrl(value) {
  try {
    const url = new URL(value);
    url.search = url.search ? '?[redacted]' : '';
    url.hash = '';
    return url.toString();
  } catch {
    return '[invalid-url]';
  }
}

async function collectFrameSnapshot(page) {
  const frames = page.frames();
  const frameInfo = frames.map((frame) => ({
    url: redactUrl(frame.url()),
    name: frame.name() || null,
  }));
  const textByFrame = [];
  for (const frame of frames) {
    try {
      const text = await frame.locator('body').innerText({ timeout: 3000 });
      if (text.trim()) textByFrame.push({ url: redactUrl(frame.url()), text: text.slice(0, 50000) });
    } catch {
      // Cross-origin, detached, or canvas-only frames may have no readable DOM text.
    }
  }
  const visibleText = textByFrame.map((entry) => entry.text).join('\n');
  return { frameCount: frames.length, frames: frameInfo, textByFrame, visibleText: visibleText.slice(0, 200000) };
}

module.exports = { collectFrameSnapshot, redactUrl };
