// 检查是否为有效链接
const isValidUrl = (url) => {
    const urlRegex = /http[s]?:\/\/[^\s]+/;
    return urlRegex.test(url);
};

// 检查是否为支持的平台（仅QQ音乐）
const isSupportedPlatform = (url) => {
    return /qq\.com/.test(url);
};


export {isValidUrl, isSupportedPlatform};