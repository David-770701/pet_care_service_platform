;(function () {
  const DATA_URL = 'https://cdn.jsdelivr.net/npm/china-regions-data@0.0.3/list.json'

  async function fetchJson(url) {
    const resp = await fetch(url)
    if (!resp.ok) throw new Error('Request failed: ' + resp.status)
    return await resp.json()
  }

  function fillOptions(selectEl, items, placeholder) {
    selectEl.innerHTML = ''
    const placeholderOpt = document.createElement('option')
    placeholderOpt.value = ''
    placeholderOpt.textContent = placeholder
    selectEl.appendChild(placeholderOpt)
    items.forEach(function (name) {
      const opt = document.createElement('option')
      opt.value = name
      opt.textContent = name
      selectEl.appendChild(opt)
    })
  }

  function setValueIfExists(selectEl, value) {
    if (!value) return
    const option = Array.from(selectEl.options).find(function (o) {
      return o.value === value
    })
    if (option) selectEl.value = value
  }

  function uniqSorted(arr) {
    return Array.from(new Set(arr)).sort(function (a, b) {
      return a.localeCompare(b, 'zh-Hans-CN')
    })
  }

  function buildIndexes(codeToName) {
    const provinces = []
    const provinceCodeToName = {}
    const provinceNameToCode = {}

    const EXCLUDED_PROVINCES = new Set(['香港特别行政区', '澳门特别行政区', '台湾省'])

    Object.keys(codeToName).forEach(function (code) {
      if (code.length !== 6) return
      if (code.endsWith('0000')) {
        const name = codeToName[code]
        if (EXCLUDED_PROVINCES.has(name)) return
        provinces.push(name)
        provinceCodeToName[code] = name
        provinceNameToCode[name] = code
      }
    })

    function cityCodesByProvince(provinceCode) {
      const prefix = provinceCode.slice(0, 2)
      const out = []
      Object.keys(codeToName).forEach(function (code) {
        if (code.length !== 6) return
        if (!code.startsWith(prefix)) return
        if (code.endsWith('00') && !code.endsWith('0000')) out.push(code)
      })
      return out
    }

    function districtCodesByCity(cityCode) {
      const prefix = cityCode.slice(0, 4)
      const out = []
      Object.keys(codeToName).forEach(function (code) {
        if (code.length !== 6) return
        if (!code.startsWith(prefix)) return
        if (!code.endsWith('00')) out.push(code)
      })
      return out
    }

    function districtCodesByProvince(provinceCode) {
      const prefix = provinceCode.slice(0, 2)
      const out = []
      Object.keys(codeToName).forEach(function (code) {
        if (code.length !== 6) return
        if (!code.startsWith(prefix)) return
        if (!code.endsWith('00')) out.push(code)
      })
      return out
    }

    function cityNamesByProvinceName(provinceName) {
      const MUNICIPALITIES = new Set(['北京市', '上海市', '天津市', '重庆市'])
      if (MUNICIPALITIES.has(provinceName)) {
        return [provinceName]
      }
      const provinceCode = provinceNameToCode[provinceName]
      if (!provinceCode) return []
      const cityCodes = cityCodesByProvince(provinceCode)
      if (cityCodes.length === 0) {
        return [provinceName]
      }
      const names = cityCodes.map(function (c) {
        return codeToName[c]
      })
      return uniqSorted(names)
    }

    function districtNamesByProvinceCity(provinceName, cityName) {
      const provinceCode = provinceNameToCode[provinceName]
      if (!provinceCode) return []
      if (provinceName === cityName) {
        const dCodes = districtCodesByProvince(provinceCode)
        const names = dCodes.map(function (dc) {
          return codeToName[dc]
        })
        return uniqSorted(names)
      }
      const cityCodes = cityCodesByProvince(provinceCode)
      if (cityCodes.length === 0) {
        const dCodes = districtCodesByProvince(provinceCode)
        const names = dCodes.map(function (dc) {
          return codeToName[dc]
        })
        return uniqSorted(names)
      }
      const cityCode = cityCodes.find(function (cc) {
        return codeToName[cc] === cityName
      })
      if (!cityCode) return []
      const dCodes = districtCodesByCity(cityCode)
      const names = dCodes.map(function (dc) {
        return codeToName[dc]
      })
      return uniqSorted(names)
    }

    return {
      provinces: uniqSorted(provinces),
      cityNamesByProvinceName,
      districtNamesByProvinceCity
    }
  }

  async function initCnProvinceCityDistrict(opts) {
    const provinceEl = document.getElementById(opts.provinceSelectId)
    const cityEl = document.getElementById(opts.citySelectId)
    const districtEl = document.getElementById(opts.districtSelectId)
    if (!provinceEl || !cityEl || !districtEl) return

    const initialProvince = opts.initialProvince || ''
    const initialCity = opts.initialCity || ''
    const initialDistrict = opts.initialDistrict || ''

    cityEl.disabled = true
    districtEl.disabled = true

    let codeToName
    try {
      codeToName = await fetchJson(DATA_URL)
    } catch (e) {
      fillOptions(provinceEl, [], '行政区数据加载失败')
      fillOptions(cityEl, [], '行政区数据加载失败')
      fillOptions(districtEl, [], '行政区数据加载失败')
      return
    }

    const idx = buildIndexes(codeToName)
    fillOptions(provinceEl, idx.provinces, '请选择省份')
    fillOptions(cityEl, [], '请先选择省份')
    fillOptions(districtEl, [], '请先选择城市')

    function onProvinceChange() {
      const p = provinceEl.value
      if (!p) {
        fillOptions(cityEl, [], '请先选择省份')
        fillOptions(districtEl, [], '请先选择城市')
        cityEl.disabled = true
        districtEl.disabled = true
        return
      }
      const cities = idx.cityNamesByProvinceName(p)
      fillOptions(cityEl, cities, '请选择城市')
      fillOptions(districtEl, [], '请先选择城市')
      cityEl.disabled = false
      districtEl.disabled = true

      if (cities.length === 1 && cities[0] === p) {
        cityEl.value = p
        cityEl.disabled = false
        onCityChange()
      }
    }

    function onCityChange() {
      const p = provinceEl.value
      const c = cityEl.value
      if (!p || !c) {
        fillOptions(districtEl, [], '请先选择城市')
        districtEl.disabled = true
        return
      }
      const districts = idx.districtNamesByProvinceCity(p, c)
      fillOptions(districtEl, districts, '请选择区/县')
      districtEl.disabled = false
    }

    provinceEl.addEventListener('change', function () {
      onProvinceChange()
    })
    cityEl.addEventListener('change', function () {
      onCityChange()
    })

    setValueIfExists(provinceEl, initialProvince)
    onProvinceChange()
    setValueIfExists(cityEl, initialCity)
    onCityChange()
    setValueIfExists(districtEl, initialDistrict)
  }

  window.initCnProvinceCityDistrict = initCnProvinceCityDistrict
})()
