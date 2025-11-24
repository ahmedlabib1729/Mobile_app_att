/** @odoo-module **/

import { AcsDashChartData } from './acs_dash_chart_data';

const chartBackendData = new AcsDashChartData();

async function acsBarChartValue(chartContainer, dataMethod) {
    am4core.useTheme(am4themes_animated);

    var chart = am4core.create(chartContainer, am4charts.XYChart);
    chart.scrollbarX = new am4core.Scrollbar();
    chart.logo.disabled = true;

    const result = await dataMethod();
    const { labels, data, tooltiptext } = result;

    const chartData = labels.map((label, index) => ({
        date: label,
        appointments: data[index],
        tooltiptext: tooltiptext[index]
    }));
    chart.data = chartData;
    if (chart.data.length === 0) {
        console.warn(`No data to display for the '${chartContainer}' chart.`);
        return;
    }

    var categoryAxis = chart.xAxes.push(new am4charts.CategoryAxis());
    categoryAxis.dataFields.category = "date";
    categoryAxis.renderer.grid.template.location = 0;
    categoryAxis.renderer.minGridDistance = 20;
    categoryAxis.renderer.labels.template.horizontalCenter = "right";
    categoryAxis.renderer.labels.template.verticalCenter = "middle";
    categoryAxis.renderer.labels.template.wrap = true;
    categoryAxis.renderer.labels.template.maxWidth = 120;
    categoryAxis.renderer.labels.template.rotation = 270;
    categoryAxis.tooltip.disabled = true;
    categoryAxis.renderer.labels.template.fill = am4core.color("#1B1833");

    categoryAxis.start = Math.max(0, 1 - 10 / chart.data.length);
    categoryAxis.end = 1;
    categoryAxis.keepSelection = true;

    var valueAxis = chart.yAxes.push(new am4charts.ValueAxis());
    valueAxis.renderer.minWidth = 50;
    valueAxis.renderer.labels.template.fill = am4core.color("#1B1833");

    var series = chart.series.push(new am4charts.ColumnSeries());
    series.sequencedInterpolation = true;
    series.dataFields.valueY = "appointments";
    series.dataFields.categoryX = "date";
    series.tooltipText = "{tooltiptext}: {appointments}";
    series.columns.template.strokeWidth = 0;

    series.tooltip.pointerOrientation = "vertical";
    series.columns.template.column.cornerRadiusTopLeft = 10;
    series.columns.template.column.cornerRadiusTopRight = 10;
    series.columns.template.column.fillOpacity = 0.8;

    let hoverState = series.columns.template.column.states.create("hover");
    hoverState.properties.cornerRadiusTopLeft = 0;
    hoverState.properties.cornerRadiusTopRight = 0;
    hoverState.properties.fillOpacity = 1;

    series.columns.template.adapter.add("fill", (fill, target) => {
        return chart.colors.getIndex(target.dataItem.index);
    });

    chart.cursor = new am4charts.XYCursor();
}

// Function to render Appointment Bar Chart
export async function renderAppointmentBarChart(appointmentBarChartContainer) {
    await acsBarChartValue(
        appointmentBarChartContainer,
        () => chartBackendData.acsFetchAppointmentData()
    );
    
    function updateChart(newRecord) {
        chartData.push(newRecord);
        if (chartData.length > 90) {
            chartData.shift();
        }
        chart.data = chartData;

        categoryAxis.start = Math.max(0, 1 - 10 / chart.data.length);
        categoryAxis.end = 1;
    }
}

// Function to render Patient Disease Bar Chart
export async function renderPatientDiseaseBarChart(patientDiseaseBarChartContainer, domain=[]) {
    await acsBarChartValue(
        patientDiseaseBarChartContainer,
        () => chartBackendData.acsFetchPatientDiseaseData(domain)
    );
}

// Function to render Patient State By Country Bar Chart
export async function renderPatientStateBarChart(container, domain=[]) {
    if (!container) {
        console.error("Chart container not found.");
        return;
    }

    let chartDiv;
    let chart;

    if (!container.querySelector("select")) {
        const dropdownWrapper = document.createElement("div");
        dropdownWrapper.className = "d-flex justify-content-center px-2 mb-2";

        const dropdown = document.createElement("select");
        dropdown.className = "form-select form-select-sm";
        dropdown.style.borderRadius = "8px";
        dropdown.style.padding = "8px 12px";
        dropdown.style.border = "2px solid #007bff";
        dropdown.style.textAlignLast = "center";
        dropdown.style.boxSizing = "border-box";

        dropdown.innerHTML = `
            <option value="" disabled selected hidden style="color: #888; font-style: italic;">
                🌍 Select Country
            </option>
        `;

        dropdownWrapper.appendChild(dropdown);
        container.appendChild(dropdownWrapper);

        const countries = await chartBackendData.acsFetchAllCountriesData();
        countries.forEach(country => {
            const option = document.createElement("option");
            option.value = country.id;
            option.textContent = country.name;
            dropdown.appendChild(option);
        });

        chartDiv = document.createElement("div");
        chartDiv.style.height = "460px";
        chartDiv.style.width = "100%";
        container.appendChild(chartDiv);

        dropdown.addEventListener("change", () => {
            const selectedId = dropdown.value ? parseInt(dropdown.value) : null;
            drawChart(selectedId);
        });
    } else {
        chartDiv = container.querySelector("div[style*='height: 460px']");
    }

    async function drawChart(countryId = null) {
        if (chart) {
            chart.dispose();
        }

        chartDiv.innerHTML = "";

        const data = await chartBackendData.acsFetchPatientStateByCountryData(countryId, domain);

        if (!data.length) {
            chartDiv.innerHTML = `<p style="text-align:center; color:#888;">No data available.</p>`;
            return;
        }

        am4core.useTheme(am4themes_animated);
        chart = am4core.create(chartDiv, am4charts.XYChart);
        chart.logo.disabled = true;
        chart.data = data;

        let categoryAxis = chart.xAxes.push(new am4charts.CategoryAxis());
        categoryAxis.dataFields.category = "category";
        categoryAxis.renderer.grid.template.location = 0;
        categoryAxis.renderer.labels.template.rotation = -90;
        categoryAxis.renderer.labels.template.horizontalCenter = "left";
        categoryAxis.renderer.labels.template.verticalCenter = "middle";
        categoryAxis.renderer.minGridDistance = 1;
        categoryAxis.renderer.labels.template.truncate = false;
        categoryAxis.renderer.labels.template.hideOversized = false;

        categoryAxis.start = Math.max(0, 1 - 10 / chart.data.length);
        categoryAxis.end = 1;
        categoryAxis.keepSelection = true;

        let valueAxis = chart.yAxes.push(new am4charts.ValueAxis());
        let series = chart.series.push(new am4charts.ColumnSeries());
        series.dataFields.valueY = "value";
        series.dataFields.categoryX = "category";
        series.name = "Patient Count";
        series.columns.template.tooltipText = "{category}: {valueY}";
        series.columns.template.fillOpacity = 0.8;

        let columnTemplate = series.columns.template;
        columnTemplate.strokeWidth = 0;
        columnTemplate.strokeOpacity = 0;

        chart.scrollbarX = new am4core.Scrollbar();
        chart.scrollbarX.marginBottom = 20;
        chart.scrollbarY = new am4core.Scrollbar();
        chart.cursor = new am4charts.XYCursor();
        chart.cursor.behavior = "panX";
        chart.cursor.lineX.disabled = true;
        chart.cursor.lineY.disabled = true;
    }

    drawChart();
}

// Function to render Patient Line Chart
export async function renderPatientLineChart(patientLineChartContainer) {
    am4core.useTheme(am4themes_animated);

    var chart = am4core.create(patientLineChartContainer, am4charts.XYChart);
    chart.scrollbarX = new am4core.Scrollbar();
    chart.logo.disabled = true;

    const result = await chartBackendData.acsFetchPatientData();

    if (result) {
        const { labels, data } = result;

        const chartData = labels.map((label, index) => ({
            date: new Date(label), // Ensure proper date format
            value: data[index]
        }));

        chart.data = chartData;

        var dateAxis = chart.xAxes.push(new am4charts.DateAxis());
        dateAxis.renderer.labels.template.fill = am4core.color("#1B1833");
        dateAxis.baseInterval = { timeUnit: "day", count: 1 };
        dateAxis.groupData = true;
        dateAxis.skipEmptyPeriods = true;

        var valueAxis = chart.yAxes.push(new am4charts.ValueAxis());
        valueAxis.renderer.labels.template.fill = am4core.color("#1B1833");

        var series = chart.series.push(new am4charts.LineSeries());
        series.dataFields.valueY = "value";
        series.dataFields.dateX = "date";
        series.tooltipText = "{dateX.formatDate('MMM dd, yyyy')}: {value}";
        series.strokeWidth = 2;
        series.minBulletDistance = 15;

        series.tooltip.background.cornerRadius = 20;
        series.tooltip.background.strokeOpacity = 0;
        series.tooltip.pointerOrientation = "vertical";
        series.tooltip.label.minWidth = 40;
        series.tooltip.label.minHeight = 40;
        series.tooltip.label.textAlign = "middle";
        series.tooltip.label.textValign = "middle";

        var bullet = series.bullets.push(new am4charts.CircleBullet());
        bullet.circle.strokeWidth = 2;
        bullet.circle.radius = 4;
        bullet.circle.fill = am4core.color("#fff");

        var bullethover = bullet.states.create("hover");
        bullethover.properties.scale = 1.3;

        chart.cursor = new am4charts.XYCursor();
        chart.cursor.behavior = "panXY";
        chart.cursor.xAxis = dateAxis;
        chart.cursor.snapToSeries = series;
    } else {
        console.error("Failed to fetch patient data");
    }
}

async function acsPieChartValue(chartContainer, dataMethod) {
    am4core.useTheme(am4themes_animated);
    if (chartContainer.chart) {
        chartContainer.chart.dispose();
    }
    var chart = am4core.create(chartContainer, am4charts.PieChart);
    chart.logo.disabled = true;
    const result = await dataMethod();
    return { chart, result };
}

async function acsPieChartSeriesValue(chart, valueField, categoryField, options = {}) {
    const pieSeries = chart.series.push(new am4charts.PieSeries());
    pieSeries.dataFields.value = valueField;
    pieSeries.dataFields.category = categoryField;
    pieSeries.slices.template.stroke = am4core.color("#fff");
    pieSeries.slices.template.strokeWidth = 2;
    pieSeries.slices.template.strokeOpacity = 1;
    pieSeries.labels.template.fill = am4core.color("#9aa0ac");
    pieSeries.slices.template.tooltipText = "{category}: {value.percent.formatNumber('#.0')}% ({value})";
    pieSeries.labels.template.disabled = true;
    pieSeries.ticks.template.disabled = true;
    pieSeries.hiddenState.properties.opacity = 1;
    pieSeries.hiddenState.properties.endAngle = -90;
    pieSeries.hiddenState.properties.startAngle = -90;

    chart.legend = new am4charts.Legend();

    if (options.legendPosition) chart.legend.position = options.legendPosition;
    if (options.legendMaxHeight) chart.legend.maxHeight = options.legendMaxHeight;
    if (options.legendMaxWidth) chart.legend.maxWidth = options.legendMaxWidth;
    if (options.legendScrollable) chart.legend.scrollable = true;
    if (options.legendFontSize) {
        chart.legend.labels.template.fontSize = options.legendFontSize;
        chart.legend.valueLabels.template.fontSize = options.legendFontSize;
    }
    if (options.legendMarkerSize) {
        chart.legend.markers.template.width = options.legendMarkerSize;
        chart.legend.markers.template.height = options.legendMarkerSize;
    }
    if (options.legendItemPadding !== undefined) {
        chart.legend.itemContainers.template.paddingTop = options.legendItemPadding;
        chart.legend.itemContainers.template.paddingBottom = options.legendItemPadding;
    }
    if (options.legendLabelWrap) {
        chart.legend.labels.template.wrap = true;
        chart.legend.labels.template.maxWidth = options.legendLabelWidth || 120;
    }

    chart.legend.width = am4core.percent(100);
    chart.legend.labels.template.fill = am4core.color("#9aa0ac");
    chart.legend.valueLabels.template.fill = am4core.color("#9aa0ac");
}

// Function to render Patient Gender Pie Chart
export async function renderPatientGenderPieChart(patientGenderPieChartContainer, domain=[]) {
    const { chart, result } = await acsPieChartValue(
        patientGenderPieChartContainer,
        () => chartBackendData.acsFetchPatientGenderData(domain)
    );

    if (!result || result.length === 0) {
        patientGenderPieChartContainer.innerHTML = "<p style='text-align: center; color: #9aa0ac;'>No gender data to display.</p>";
        return;
    }

    chart.data = result.map(item => ({
        gender: item.gender,
        patient_count: item.count
    }));

    await acsPieChartSeriesValue(chart, "patient_count", "gender");
}

// Function to render Patient Country Pie Chart
export async function renderPatientCountryPieChart(patientCountryPieContainer, domain=[]) {
    const { chart, result } = await acsPieChartValue(
        patientCountryPieContainer,
        () => chartBackendData.acsFetchPatientCountryData(domain)
    );

    if (!result || result.length === 0) {
        patientCountryPieContainer.innerHTML = "<p style='text-align: center; color: #9aa0ac;'>No country data to display.</p>";
        return;
    }

    const sortedTop10 = result
        .sort((a, b) => b.value - a.value)
        .slice(0, 10);

    chart.data = sortedTop10.map(item => ({
        country: item.category,
        patient_count: item.value,
        id: item.id
    }));

    await acsPieChartSeriesValue(chart, "patient_count", "country", {
        legendPosition: "left",
        legendMaxHeight: 300,
        legendMaxWidth: 250,
        legendScrollable: false,
        legendLabelWrap: true,
        legendLabelWidth: 100,
        legendFontSize: 16,
        legendMarkerSize: 16,
        legendItemPadding: 2
    });
}

// Function to render Patient Age Gauge Chart
export async function renderPatientAgeGaugeChart(patientAgeGaugeChartContainer, domain=[]) {
    am4core.useTheme(am4themes_animated);
    var chart = am4core.create(patientAgeGaugeChartContainer, am4charts.RadarChart);
    chart.logo.disabled = true;

    const rawData = await chartBackendData.acsFetchPatientAgeGrpData(domain);

    const total = rawData.reduce((sum, item) => sum + item.count, 0);
    const processedData = rawData.map(item => ({
        age_group: item.age_group,
        count: total > 0 ? (item.count / total) * 100 : 0,
        full: 100,
        actual_count: item.count
    }));

    chart.data = processedData;
    chart.startAngle = -90;
    chart.endAngle = 180;
    chart.innerRadius = am4core.percent(20);
    chart.numberFormatter.numberFormat = "#.#'%'";
    var categoryAxis = chart.yAxes.push(new am4charts.CategoryAxis());
    categoryAxis.dataFields.category = "age_group";
    categoryAxis.renderer.grid.template.location = 0;
    categoryAxis.renderer.grid.template.strokeOpacity = 0;
    categoryAxis.renderer.labels.template.horizontalCenter = "right";
    categoryAxis.renderer.labels.template.fontWeight = 500;
    categoryAxis.renderer.labels.template.adapter.add("fill", function (fill, target) {
        return (target.dataItem.index >= 0) ? chart.colors.getIndex(target.dataItem.index) : fill;
    });
    categoryAxis.renderer.minGridDistance = 10;
    var valueAxis = chart.xAxes.push(new am4charts.ValueAxis());
    valueAxis.renderer.grid.template.strokeOpacity = 0;
    valueAxis.min = 0;
    valueAxis.max = 100;
    valueAxis.strictMinMax = true;
    valueAxis.renderer.labels.template.fill = am4core.color("#9aa0ac");
    var series1 = chart.series.push(new am4charts.RadarColumnSeries());
    series1.dataFields.valueX = "full";
    series1.dataFields.categoryY = "age_group";
    series1.clustered = false;
    series1.columns.template.fill = new am4core.InterfaceColorSet().getFor("alternativeBackground");
    series1.columns.template.fillOpacity = 0.08;
    series1.columns.template.cornerRadiusTopLeft = 20;
    series1.columns.template.strokeWidth = 0;
    series1.columns.template.radarColumn.cornerRadius = 20;
    var series2 = chart.series.push(new am4charts.RadarColumnSeries());
    series2.dataFields.valueX = "count";
    series2.dataFields.categoryY = "age_group";
    series2.clustered = false;
    series2.columns.template.strokeWidth = 0;
    series2.columns.template.tooltipText = "{age_group}: [bold]{valueX}[/] patients ({actual_count.formatNumber('#.#')})";
    series2.columns.template.radarColumn.cornerRadius = 20;
    series2.columns.template.adapter.add("fill", function (fill, target) {
        return chart.colors.getIndex(target.dataItem.index);
    });
    chart.cursor = new am4charts.RadarCursor();
}

// Function to render Patient Department Donut Chart
export async function renderDepartmentDonutChart(departmentDonutChartContainer, domain=[]) {
    if (!departmentDonutChartContainer) {
        console.warn("Donut chart container is null or undefined.");
        return;
    }

    am4core.useTheme(am4themes_animated);
    if (departmentDonutChartContainer.chart) {
        departmentDonutChartContainer.chart.dispose();
    }

    const data = await chartBackendData.acsFetchPatientDepartmentData(domain);
    if (!data || data.length === 0) {
        console.warn("No department patient data available for chart.");
        departmentDonutChartContainer.innerHTML = "<p style='text-align: center; color: #9aa0ac;'>No department data to display.</p>";
        return;
    }

    const chart = am4core.create(departmentDonutChartContainer, am4charts.PieChart);
    chart.logo.disabled = true;
    departmentDonutChartContainer.chart = chart;

    chart.innerRadius = am4core.percent(50);
    chart.data = data;

    const pieSeries = chart.series.push(new am4charts.PieSeries());
    pieSeries.dataFields.value = "count";
    pieSeries.dataFields.category = "department";
    pieSeries.slices.template.stroke = am4core.color("#fff");
    pieSeries.slices.template.strokeWidth = 2;
    pieSeries.slices.template.strokeOpacity = 1;
    pieSeries.labels.template.fill = am4core.color("#333");
    pieSeries.labels.template.fontSize = 16;
    pieSeries.labels.template.wrap = true;
    pieSeries.labels.template.truncate = false;
    pieSeries.labels.template.maxWidth = 140;
    pieSeries.hiddenState.properties.opacity = 1;
    pieSeries.hiddenState.properties.endAngle = -90;
    pieSeries.hiddenState.properties.startAngle = -90;
    // pieSeries.labels.template.fontWeight = "bold";
}

export async function renderMedicalServicesLineChart(chartDivId, domain = []) {
    am4core.ready(async function () {
        if (am4core.registry.baseSprites.length) {
            am4core.registry.baseSprites.forEach(sprite => {
                if (sprite.htmlContainer.id === chartDivId) {
                    sprite.dispose();
                }
            });
        }

        am4core.useTheme(am4themes_animated);

        const chartData = await chartBackendData.acsFetchMedicalServicesData(domain);
        if (!chartData || !chartData.series || !chartData.categories) {
            console.warn("Invalid chart data");
            return;
        }

        let data = chartData.categories.map((cat, i) => {
            return {
                date: cat,
                totalAmount: chartData.series.find(s => s.name === "Total Amount")?.data[i] || 0,
                totalQuantity: chartData.series.find(s => s.name === "Total Quantity")?.data[i] || 0
            };
        });

        var chart = am4core.create(chartDivId, am4charts.XYChart);
        chart.data = data;
        chart.logo.disabled = true;

        var categoryAxis = chart.xAxes.push(new am4charts.CategoryAxis());
        categoryAxis.dataFields.category = "date";
        categoryAxis.renderer.grid.template.location = 0;
        categoryAxis.renderer.minGridDistance = 50;
        categoryAxis.renderer.labels.template.rotation = -90;
        categoryAxis.renderer.labels.template.wrap = true;
        categoryAxis.renderer.labels.template.maxWidth = 120;
        categoryAxis.renderer.labels.template.horizontalCenter = "right";
        categoryAxis.renderer.labels.template.verticalCenter = "middle";

        var amountAxis = chart.yAxes.push(new am4charts.ValueAxis());
        amountAxis.title.text = "Total Amount";

        var quantityAxis = chart.yAxes.push(new am4charts.ValueAxis());
        quantityAxis.title.text = "Total Quantity";
        quantityAxis.renderer.opposite = true;
        quantityAxis.syncWithAxis = amountAxis;

        var amountSeries = chart.series.push(new am4charts.ColumnSeries());
        amountSeries.dataFields.valueY = "totalAmount";
        amountSeries.dataFields.categoryX = "date";
        amountSeries.yAxis = amountAxis;
        amountSeries.name = "Total Amount";
        amountSeries.tooltipText = "{name}: [bold]{valueY}[/]";
        amountSeries.columns.template.fillOpacity = 0.7;

        var quantitySeries = chart.series.push(new am4charts.LineSeries());
        quantitySeries.dataFields.valueY = "totalQuantity";
        quantitySeries.dataFields.categoryX = "date";
        quantitySeries.yAxis = quantityAxis;
        quantitySeries.name = "Total Quantity";
        quantitySeries.strokeWidth = 2;
        quantitySeries.tooltipText = "{name}: [bold]{valueY}[/]";

        var bullet = quantitySeries.bullets.push(new am4charts.CircleBullet());
        bullet.circle.fill = am4core.color("#fff");
        bullet.circle.strokeWidth = 2;

        chart.legend = new am4charts.Legend();

        chart.cursor = new am4charts.XYCursor();
        chart.cursor.behavior = "zoomX";
        chart.cursor.xAxis = categoryAxis;

        chart.scrollbarX = new am4core.Scrollbar();
    });
}
