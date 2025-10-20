/**
 * Task data transformation utilities.
 */

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
