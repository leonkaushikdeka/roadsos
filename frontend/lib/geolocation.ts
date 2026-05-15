export type GeoPermissionState = "granted" | "denied" | "prompt" | "unsupported";

export async function getGeolocationPermissionState(): Promise<GeoPermissionState> {
  if (!navigator.geolocation) return "unsupported";
  if (!navigator.permissions) return "prompt"; // assume prompt if API unavailable
  try {
    const status = await navigator.permissions.query({ name: "geolocation" });
    return status.state as GeoPermissionState;
  } catch {
    return "prompt";
  }
}

export function getCurrentPosition(options?: PositionOptions): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Geolocation not supported on this device"));
      return;
    }

    navigator.geolocation.getCurrentPosition(resolve, reject, {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 0, // never use cached position
      ...options,
    });
  });
}

export function watchPosition(
  callback: (pos: GeolocationPosition) => void,
  onError?: (err: GeolocationPositionError) => void,
  options?: PositionOptions,
): number {
  if (!navigator.geolocation) {
    onError?.(new GeolocationPositionError());
    return 0;
  }

  return navigator.geolocation.watchPosition(callback, onError, {
    enableHighAccuracy: true,
    timeout: 10000,
    maximumAge: 0,
    ...options,
  });
}

export async function getLocationName(lat: number, lng: number): Promise<string> {
  try {
    const resp = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=16&accept-language=en`,
      { headers: { "User-Agent": "RoadSoS/1.0" } },
    );
    const data = await resp.json();
    return data.display_name || `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
  } catch {
    return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
  }
}
