export function deviceDate(device) {
  const value = device.lastActive || device.last_active || device.updated_at || device.createdAt || device.created_at;
  if (!value) return 'Unknown';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Unknown' : date.toLocaleString();
}
