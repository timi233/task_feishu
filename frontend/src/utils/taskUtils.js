/**
 * Task data transformation utilities.
 */

/**
 * 将毫秒时间戳转换为日期字符串 (YYYY-MM-DD)，使用本地时间
 */
function timestampToDateString(timestamp) {
    if (!timestamp) return null;
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return null;
    // 使用本地时间而非UTC，避免时区导致的日期偏移
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

/**
 * 根据日期获取星期几的 key
 */
function getWeekdayKey(dateStr) {
    if (!dateStr) return 'unknown_date';
    const date = new Date(dateStr);
    if (Number.isNaN(date.getTime())) return 'unknown_date';

    const dayIndex = date.getDay(); // 0=Sunday, 1=Monday, ..., 6=Saturday
    const weekdayMap = {
        0: 'weekend',
        1: 'monday',
        2: 'tuesday',
        3: 'wednesday',
        4: 'thursday',
        5: 'friday',
        6: 'weekend',
    };
    return weekdayMap[dayIndex] || 'unknown_date';
}

/**
 * 将任意字段值（字符串/数组/对象）归一化为字符串数组
 */
function normalizeEngineerField(value) {
    if (!value) return [];

    if (Array.isArray(value)) {
        return value
            .map((item) => {
                if (!item) return '';
                if (typeof item === 'string') return item;
                if (typeof item === 'object') {
                    return item.name || item.text || item.value || '';
                }
                return String(item);
            })
            .filter(Boolean);
    }

    if (typeof value === 'object') {
        const candidate = value.name || value.text || value.value;
        return candidate ? [candidate] : [];
    }

    if (typeof value === 'string') {
        return [value];
    }

    return [String(value)];
}

/**
 * 解析工程师名字字段，拆分多个工程师，并在主字段只有一个时回退到当前处理人
 * @param {string|Array|Object} engineerField 派工单的工程师字段（可能是字符串/数组）
 * @param {string|Array|Object} fallbackField 备用字段，例如当前处理人
 * @returns {Array<string>} 工程师名字数组
 */
function parseEngineerNames(engineerField, fallbackField = null) {
    const delimiter = /[，,、;；\/|\n\r]+/;
    const dedupedNames = [];

    const extractNames = (value) => {
        const result = [];
        normalizeEngineerField(value).forEach((raw) => {
            raw.split(delimiter)
                .map((name) => name.trim())
                .filter(Boolean)
                .forEach((name) => result.push(name));
        });
        return result;
    };

    const appendNames = (names) => {
        names.forEach((name) => {
            if (!dedupedNames.includes(name)) {
                dedupedNames.push(name);
            }
        });
    };

    appendNames(extractNames(engineerField));

    if (fallbackField) {
        const fallbackNames = extractNames(fallbackField);
        const needsFallback =
            dedupedNames.length === 0 ||
            (dedupedNames.length === 1 && dedupedNames[0] === '未分配') ||
            fallbackNames.length >= 2;

        if (needsFallback) {
            appendNames(fallbackNames);
        }
    }

    return dedupedNames.length > 0 ? dedupedNames : ['未分配'];
}

/**
 * 将派工单数据转换为任务格式
 * @param {Object} order 派工单对象
 * @param {string} dateStr 指定的日期字符串（用于跨天任务）
 * @param {string} assigneeOverride 指定的执行人（用于多工程师拆分）
 * @returns {Object} 任务格式对象
 */
export function convertDispatchOrderToTask(order, dateStr = null, assigneeOverride = null) {
    if (!order) return null;

    const effectiveDateStr = dateStr || timestampToDateString(order.service_start_time);
    const taskName = order.customer_company && order.work_content
        ? `${order.customer_company} - ${order.work_content}`
        : order.customer_company || order.work_content || order.approval_code || '未命名派工单';

    // 对于爱数原厂派单，使用厂家对接人代替提交人
    const isEisooDispatch = order.order_type === 'eisoo_dispatch';
    const dispatchCategory = isEisooDispatch ? '厂家外勤派单' : '公司外勤派单';
    const creatorLabel = isEisooDispatch ? '厂家对接人' : '提交';
    const creatorValue = isEisooDispatch
        ? (order.vendor_contact || order.submitter_name || '未知')
        : (order.submitter_name || '未知');

    // 使用指定的执行人或原始值；外勤数据无工程师时回退到提交人
    let assignee = assigneeOverride || order.engineer_name || null;
    if (!assignee) {
        const isFieldDispatch = order?.extra_data?._source_table === 'field_dispatch';
        if (isFieldDispatch && order.submitter_name) {
            assignee = order.submitter_name;
        }
    }
    if (!assignee) {
        assignee = '未分配';
    }

    return {
        record_id: order.source_id || `dispatch-${order.id}`,
        task_name: taskName,
        creator_name: creatorValue,
        creator_label: creatorLabel,
        assignee,
        priority: order.priority || '普通',
        status: dispatchCategory,
        dispatch_category: dispatchCategory,
        approval_status: order.approval_status || '待处理',
        date: effectiveDateStr,
        // 额外字段用于识别来源
        source_table: order?.extra_data?._source_table,
        source_type: 'dispatch_order',
        order_type: order.order_type,
        source_id: order.source_id,
        // 保存原始时间范围
        start_date: timestampToDateString(order.service_start_time),
        end_date: timestampToDateString(order.service_end_time),
    };
}

/**
 * 将派工单拆分为多个任务（按工程师拆分）
 * @param {Object} order 派工单对象
 * @returns {Array<Object>} 拆分后的派工单数组，每个工程师一个
 */
function splitOrderByEngineers(order) {
    if (!order) return [];
    const engineers = parseEngineerNames(order.engineer_name, order.current_handler);
    // 为每个工程师创建一个派工单副本
    return engineers.map((engineer) => ({
        ...order,
        _assignee_override: engineer,
    }));
}

/**
 * 去重派工单（同一审批编号仅保留最新同步的一条）
 * @param {Array<Object>} orders
 * @returns {Array<Object>}
 */
function deduplicateDispatchOrders(orders) {
    if (!Array.isArray(orders)) return [];

    const latestByApproval = new Map();
    const resolveTimestamp = (order) => {
        const candidate = order?.synced_at
            || order?.updated_at
            || order?.complete_time
            || order?.submit_time;
        const ts = candidate ? new Date(candidate).getTime() : 0;
        return Number.isNaN(ts) ? 0 : ts;
    };

    orders.forEach((order) => {
        if (!order) return;
        const key = order.approval_code || order.source_id || order.id;
        const currentTs = resolveTimestamp(order);
        const existing = latestByApproval.get(key);
        if (!existing || currentTs >= existing.timestamp) {
            latestByApproval.set(key, { order, timestamp: currentTs });
        }
    });

    return Array.from(latestByApproval.values()).map((entry) => entry.order);
}

/**
 * 获取两个日期之间的所有日期（包含起止日期）
 * @param {string} startDateStr 开始日期 YYYY-MM-DD
 * @param {string} endDateStr 结束日期 YYYY-MM-DD
 * @returns {Array<string>} 日期字符串数组
 */
function getDateRange(startDateStr, endDateStr) {
    if (!startDateStr || !endDateStr) return [startDateStr].filter(Boolean);

    const dates = [];
    const startDate = new Date(startDateStr + 'T00:00:00');
    const endDate = new Date(endDateStr + 'T00:00:00');

    if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) {
        return [startDateStr].filter(Boolean);
    }

    // 限制最大范围为30天，避免无限循环
    const maxDays = 30;
    let currentDate = new Date(startDate);
    let count = 0;

    while (currentDate <= endDate && count < maxDays) {
        const year = currentDate.getFullYear();
        const month = String(currentDate.getMonth() + 1).padStart(2, '0');
        const day = String(currentDate.getDate()).padStart(2, '0');
        dates.push(`${year}-${month}-${day}`);
        currentDate.setDate(currentDate.getDate() + 1);
        count++;
    }

    return dates;
}

/**
 * 将派工单列表按星期分组（支持跨天任务在每天都显示，支持多工程师拆分）
 * @param {Array} orders 派工单数组
 * @returns {Object} 按星期分组的任务对象
 */
export function groupDispatchOrdersByWeekday(orders) {
    const grouped = {
        monday: [],
        tuesday: [],
        wednesday: [],
        thursday: [],
        friday: [],
        weekend: [],
        unknown_date: [],
    };

    const uniqueOrders = deduplicateDispatchOrders(orders);

    uniqueOrders.forEach((order) => {
        if (!order) return;

        // 先按工程师拆分
        const splitOrders = splitOrderByEngineers(order);

        splitOrders.forEach((splitOrder) => {
            const startDateStr = timestampToDateString(splitOrder.service_start_time);
            const endDateStr = timestampToDateString(splitOrder.service_end_time);

            // 获取该任务覆盖的所有日期
            const dateRange = getDateRange(startDateStr, endDateStr);

            // 为每个日期创建一个任务副本
            dateRange.forEach((dateStr) => {
                const task = convertDispatchOrderToTask(splitOrder, dateStr, splitOrder._assignee_override);
                if (!task) return;

                const weekdayKey = getWeekdayKey(dateStr);
                if (grouped[weekdayKey]) {
                    grouped[weekdayKey].push(task);
                } else {
                    grouped.unknown_date.push(task);
                }
            });
        });
    });

    return grouped;
}

/**
 * 合并两个按星期分组的任务对象
 * @param {Object} tasks1 第一个任务对象
 * @param {Object} tasks2 第二个任务对象
 * @returns {Object} 合并后的任务对象
 */
export function mergeTasksByWeekday(tasks1, tasks2) {
    const weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'weekend', 'unknown_date'];
    const merged = {};

    weekdays.forEach((day) => {
        const arr1 = Array.isArray(tasks1?.[day]) ? tasks1[day] : [];
        const arr2 = Array.isArray(tasks2?.[day]) ? tasks2[day] : [];
        merged[day] = [...arr1, ...arr2];
    });

    return merged;
}

/**
 * Reorganize tasks grouped by day into a map grouped by engineer.
 * @param {Object} tasksByDay Tasks organized by weekday keys (monday, tuesday, etc.).
 * @returns {Object} Map where each key is an engineer name, and the value is an object with weekday keys.
 */
export function groupTasksByEngineer(tasksByDay) {
    const engineerMap = {};
    const weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'];

    weekdays.forEach((day) => {
        const dayTasks = Array.isArray(tasksByDay?.[day]) ? tasksByDay[day] : [];
        dayTasks.forEach((task) => {
            const engineer = task?.assignee || '未分配';
            if (!engineerMap[engineer]) {
                engineerMap[engineer] = {
                    monday: [],
                    tuesday: [],
                    wednesday: [],
                    thursday: [],
                    friday: [],
                };
            }
            engineerMap[engineer][day].push(task);
        });
    });

    return engineerMap;
}
