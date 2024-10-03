
export function sleep(ms) {
  return new Promise((resolve) => setTimeout(() => resolve(), ms))
}


export function chunkArray(array, chunkSize = 10) {
  const chunks = [];
  for (let i = 0; i < array.length; i += chunkSize) {
    chunks.push(array.slice(i, i + chunkSize));
  }
  return chunks;
}

export function removeDuplicate(array) {
  return [...new Set(array)]
}