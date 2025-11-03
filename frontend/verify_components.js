#!/usr/bin/env node
/**
 * 验证新创建的组件文件语法和导入
 * 运行: node verify_components.js
 */

const fs = require('fs');
const path = require('path');

const components = [
    'ConfirmDialog.js',
    'UpdateDispatchModal.js',
    'TransferDispatchModal.js',
    'DispatchOperationCard.js',
    'DispatchManagementPanel.js',
];

const componentsDir = path.join(__dirname, 'src', 'components');

console.log('🔍 验证工单管理组件...\n');

let allPassed = true;

components.forEach((component) => {
    const filePath = path.join(componentsDir, component);
    const componentName = component.replace('.js', '');

    console.log(`📄 检查 ${componentName}...`);

    // 检查文件是否存在
    if (!fs.existsSync(filePath)) {
        console.log(`   ❌ 文件不存在: ${filePath}`);
        allPassed = false;
        return;
    }

    // 读取文件内容
    const content = fs.readFileSync(filePath, 'utf-8');

    // 检查基本要素
    const checks = [
        {
            name: 'React导入',
            test: /import.*from ['"]react['"]/,
        },
        {
            name: 'PropTypes导入',
            test: /import PropTypes from ['"]prop-types['"]/,
        },
        {
            name: '默认导出',
            test: /export default function/,
        },
        {
            name: 'PropTypes定义',
            test: new RegExp(`${componentName}\\.propTypes\\s*=`),
        },
    ];

    let componentPassed = true;

    checks.forEach((check) => {
        if (check.test.test(content)) {
            console.log(`   ✅ ${check.name}`);
        } else {
            console.log(`   ❌ ${check.name} 缺失`);
            componentPassed = false;
        }
    });

    // 检查文件大小
    const stats = fs.statSync(filePath);
    const sizeKB = (stats.size / 1024).toFixed(2);
    console.log(`   📊 文件大小: ${sizeKB} KB`);

    // 检查代码行数
    const lines = content.split('\n').length;
    console.log(`   📏 代码行数: ${lines}`);

    if (componentPassed) {
        console.log(`   ✅ ${componentName} 验证通过\n`);
    } else {
        console.log(`   ❌ ${componentName} 验证失败\n`);
        allPassed = false;
    }
});

// 检查组件间依赖
console.log('🔗 检查组件依赖关系...\n');

const dependencies = [
    {
        component: 'DispatchOperationCard.js',
        imports: [
            'ConfirmDialog',
            'UpdateDispatchModal',
            'TransferDispatchModal',
        ],
    },
    {
        component: 'DispatchManagementPanel.js',
        imports: ['DispatchOperationCard'],
    },
    {
        component: 'UpdateDispatchModal.js',
        imports: ['EngineerSelector'],
    },
    {
        component: 'TransferDispatchModal.js',
        imports: ['EngineerSelector'],
    },
];

dependencies.forEach(({ component, imports }) => {
    const filePath = path.join(componentsDir, component);
    const content = fs.readFileSync(filePath, 'utf-8');

    console.log(`📦 ${component}:`);

    imports.forEach((imp) => {
        const importPattern = new RegExp(
            `import\\s+${imp}\\s+from\\s+['"]\\.\\/.*${imp}`
        );
        if (importPattern.test(content)) {
            console.log(`   ✅ 导入 ${imp}`);
        } else {
            console.log(`   ❌ 缺少导入 ${imp}`);
            allPassed = false;
        }
    });

    console.log('');
});

// 总结
console.log('📋 验证总结:');
console.log(`   组件总数: ${components.length}`);
console.log(`   状态: ${allPassed ? '✅ 全部通过' : '❌ 存在问题'}`);

process.exit(allPassed ? 0 : 1);
