/// <reference types="vite/client" />

type QtWebChannelTransport = object;

interface QtBridgeObject {
  invoke(request: string, callback: (response: string) => void): void;
}

interface QtChannel {
  objects: {
    appBridge?: QtBridgeObject;
  };
}

interface Window {
  qt?: { webChannelTransport: QtWebChannelTransport };
  QWebChannel?: new (
    transport: QtWebChannelTransport,
    callback: (channel: QtChannel) => void,
  ) => void;
}
