import { useState } from 'react';
import Input from '../ui/Input.jsx';
import Button from '../ui/Button.jsx';

const DEVICE_CATEGORIES = [
  { value: 'access_point', label: 'Access Point' },
  { value: 'switch', label: 'Switch' },
  { value: 'router', label: 'Router' },
  { value: 'firewall', label: 'Firewall' },
  { value: 'server', label: 'Server' },
  { value: 'other', label: 'Other' },
];

const EMPTY_VALUES = {
  scenario_name: '',
  device_count: '',
  hardware_cost_per_unit: '',
  licensing_cost_per_unit_year: '',
  support_cost_year_one: '',
  lifecycle_years: '5',
  device_category: 'access_point',
  // PID amendment 1.3 — additional cost categories (all optional, default 0).
  installation_cost: '',
  accessories_cost_per_unit: '',
  spares_percent: '',
  training_cost: '',
  support_cost_recurring_per_year: '',
  adjacent_recurring_cost_per_year: '',
};

/** PID amendment 1.5 — refresh-event row blanks (kept as strings until submit). */
const EMPTY_REFRESH_EVENT = { year: '3', percent_of_devices: '', cost_per_unit_override: '' };

/** Convert a saved scenario's inputs back into the string form-state shape. */
function buildInitialValues(initial) {
  if (!initial) return EMPTY_VALUES;
  const inputs = initial.inputs || {};
  const str = (v) => (v === null || v === undefined || v === 0 ? '' : String(v));
  return {
    scenario_name: initial.scenario_name ?? '',
    device_count: str(inputs.device_count),
    hardware_cost_per_unit: str(inputs.hardware_cost_per_unit),
    licensing_cost_per_unit_year: str(inputs.licensing_cost_per_unit_year),
    support_cost_year_one: str(inputs.support_cost_year_one),
    lifecycle_years: String(inputs.lifecycle_years ?? 5),
    device_category: inputs.device_category ?? 'access_point',
    installation_cost: str(inputs.installation_cost),
    accessories_cost_per_unit: str(inputs.accessories_cost_per_unit),
    spares_percent: str(inputs.spares_percent),
    training_cost: str(inputs.training_cost),
    support_cost_recurring_per_year: str(inputs.support_cost_recurring_per_year),
    adjacent_recurring_cost_per_year: str(inputs.adjacent_recurring_cost_per_year),
  };
}

function buildInitialRefreshEvents(initial) {
  if (!initial?.inputs?.refresh_events) return [];
  return initial.inputs.refresh_events.map((event) => ({
    year: String(event.year ?? 3),
    percent_of_devices: event.percent_of_devices != null ? String(event.percent_of_devices) : '',
    cost_per_unit_override:
      event.cost_per_unit_override != null ? String(event.cost_per_unit_override) : '',
  }));
}

/** True when the initial values populate any field that lives under "Advanced". */
function initialValuesHaveAdvancedData(initial) {
  if (!initial?.inputs) return false;
  const inputs = initial.inputs;
  const advancedNumeric = [
    inputs.installation_cost,
    inputs.accessories_cost_per_unit,
    inputs.spares_percent,
    inputs.training_cost,
    inputs.support_cost_recurring_per_year,
    inputs.adjacent_recurring_cost_per_year,
  ];
  if (advancedNumeric.some((n) => Number(n) > 0)) return true;
  return Array.isArray(inputs.refresh_events) && inputs.refresh_events.length > 0;
}

/** Fields that are non-negative-number-or-blank (blank → 0). */
const OPTIONAL_NONNEG_FIELDS = [
  'support_cost_year_one',
  'installation_cost',
  'accessories_cost_per_unit',
  'training_cost',
  'support_cost_recurring_per_year',
  'adjacent_recurring_cost_per_year',
];

/**
 * TcoInputForm — collects TCO inputs with inline client-side validation.
 *
 * `initialValues` (optional) pre-fills the form when re-opening it on a saved
 * scenario for "save as new version" (PID amendment 1.5).
 *
 * @param {function} onCalculate    — called with { scenario_name, inputs } on valid submit
 * @param {boolean}  calculating    — disables the form while the preview request is in-flight
 * @param {object}   [initialValues] — optional pre-fill from a saved scenario
 * @param {string}   [submitLabel]   — overrides the submit button label
 */
export default function TcoInputForm({
  onCalculate,
  calculating = false,
  initialValues = null,
  submitLabel = null,
}) {
  const [values, setValues] = useState(() => buildInitialValues(initialValues));
  const [refreshEvents, setRefreshEvents] = useState(() =>
    buildInitialRefreshEvents(initialValues)
  );
  const [fieldErrors, setFieldErrors] = useState({});
  const [refreshErrors, setRefreshErrors] = useState({});
  // Open Advanced by default when pre-fill has any advanced data, so the
  // user can see the inherited refresh events without an extra click.
  const [showAdvanced, setShowAdvanced] = useState(() =>
    initialValuesHaveAdvancedData(initialValues)
  );

  /* Immutable field update — clears the field error on change */
  const handleChange = (field) => (e) => {
    setValues((prev) => ({ ...prev, [field]: e.target.value }));
    if (fieldErrors[field]) {
      setFieldErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  /* Refresh-event row helpers — immutable updates only. */
  const updateRefreshEvent = (index, field, raw) => {
    setRefreshEvents((prev) =>
      prev.map((row, i) => (i === index ? { ...row, [field]: raw } : row))
    );
    const errorKey = `${index}.${field}`;
    if (refreshErrors[errorKey]) {
      setRefreshErrors((prev) => ({ ...prev, [errorKey]: undefined }));
    }
  };
  const addRefreshEvent = () =>
    setRefreshEvents((prev) => [...prev, { ...EMPTY_REFRESH_EVENT }]);
  const removeRefreshEvent = (index) =>
    setRefreshEvents((prev) => prev.filter((_, i) => i !== index));

  const validate = () => {
    const errors = {};

    if (!values.scenario_name.trim()) {
      errors.scenario_name = 'Scenario name is required.';
    }

    const deviceCount = Number(values.device_count);
    if (!values.device_count.trim()) {
      errors.device_count = 'Device count is required.';
    } else if (
      !Number.isInteger(deviceCount) ||
      deviceCount <= 0 ||
      String(values.device_count).includes('.')
    ) {
      errors.device_count = 'Device count must be a positive whole number.';
    }

    const hwCost = Number(values.hardware_cost_per_unit);
    if (values.hardware_cost_per_unit.trim() === '') {
      errors.hardware_cost_per_unit = 'Hardware cost per unit is required.';
    } else if (Number.isNaN(hwCost) || hwCost < 0) {
      errors.hardware_cost_per_unit = 'Must be a number ≥ 0.';
    }

    const licCost = Number(values.licensing_cost_per_unit_year);
    if (values.licensing_cost_per_unit_year.trim() === '') {
      errors.licensing_cost_per_unit_year = 'Licensing cost is required.';
    } else if (Number.isNaN(licCost) || licCost < 0) {
      errors.licensing_cost_per_unit_year = 'Must be a number ≥ 0.';
    }

    // Generic ≥ 0 check for every optional money field.
    for (const field of OPTIONAL_NONNEG_FIELDS) {
      const raw = values[field];
      if (raw !== '' && raw.trim() !== '') {
        const n = Number(raw);
        if (Number.isNaN(n) || n < 0) {
          errors[field] = 'Must be a number ≥ 0.';
        }
      }
    }

    // Spares percent: 0–100 (matches Pydantic ge=0, le=100).
    if (values.spares_percent !== '' && values.spares_percent.trim() !== '') {
      const sp = Number(values.spares_percent);
      if (Number.isNaN(sp) || sp < 0 || sp > 100) {
        errors.spares_percent = 'Spares must be between 0 and 100 (%).';
      }
    }

    const years = Number(values.lifecycle_years);
    if (!Number.isInteger(years) || years < 1 || years > 5) {
      errors.lifecycle_years = 'Lifecycle must be between 1 and 5 years.';
    }

    return errors;
  };

  /** PID amendment 1.5 — validate the refresh-event rows. */
  const validateRefreshEvents = () => {
    const errs = {};
    refreshEvents.forEach((row, i) => {
      const year = Number(row.year);
      if (!Number.isInteger(year) || year < 2 || year > 5) {
        errs[`${i}.year`] = 'Refresh year must be 2-5.';
      }
      const pct = Number(row.percent_of_devices);
      if (row.percent_of_devices === '' || row.percent_of_devices.trim?.() === '') {
        errs[`${i}.percent_of_devices`] = 'Percent of fleet is required.';
      } else if (Number.isNaN(pct) || pct <= 0 || pct > 100) {
        errs[`${i}.percent_of_devices`] = 'Percent must be 0 < pct ≤ 100.';
      }
      if (row.cost_per_unit_override !== '' && row.cost_per_unit_override.trim?.() !== '') {
        const c = Number(row.cost_per_unit_override);
        if (Number.isNaN(c) || c < 0) {
          errs[`${i}.cost_per_unit_override`] = 'Must be a number ≥ 0.';
        }
      }
    });
    return errs;
  };

  /** Convert a possibly-blank string field to a finite number, defaulting to 0. */
  const numOrZero = (raw) =>
    raw !== '' && raw.trim() !== '' ? parseFloat(raw) : 0;

  const handleSubmit = (e) => {
    e.preventDefault();

    const errors = validate();
    const refreshErrs = validateRefreshEvents();
    if (Object.keys(errors).length > 0 || Object.keys(refreshErrs).length > 0) {
      setFieldErrors(errors);
      setRefreshErrors(refreshErrs);
      return;
    }

    const payload = {
      scenario_name: values.scenario_name.trim(),
      inputs: {
        device_count: parseInt(values.device_count, 10),
        hardware_cost_per_unit: parseFloat(values.hardware_cost_per_unit),
        licensing_cost_per_unit_year: parseFloat(values.licensing_cost_per_unit_year),
        support_cost_year_one: numOrZero(values.support_cost_year_one),
        lifecycle_years: parseInt(values.lifecycle_years, 10),
        device_category: values.device_category,
        // PID amendment 1.3 — additional cost categories.
        installation_cost: numOrZero(values.installation_cost),
        accessories_cost_per_unit: numOrZero(values.accessories_cost_per_unit),
        spares_percent: numOrZero(values.spares_percent),
        training_cost: numOrZero(values.training_cost),
        support_cost_recurring_per_year: numOrZero(values.support_cost_recurring_per_year),
        adjacent_recurring_cost_per_year: numOrZero(values.adjacent_recurring_cost_per_year),
        // PID amendment 1.5 — mid-cycle refresh events.
        refresh_events: refreshEvents.map((row) => {
          const event = {
            year: parseInt(row.year, 10),
            percent_of_devices: parseFloat(row.percent_of_devices),
          };
          if (row.cost_per_unit_override !== '' && row.cost_per_unit_override.trim?.() !== '') {
            event.cost_per_unit_override = parseFloat(row.cost_per_unit_override);
          }
          return event;
        }),
      },
    };

    onCalculate(payload);
  };

  const selectBase = [
    'w-full rounded-md px-3 py-2 text-sm bg-bg text-text',
    'border border-[var(--border)] transition-colors duration-150',
    'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent',
    'focus-visible:ring-offset-2 focus-visible:ring-offset-surface',
    'disabled:opacity-40 disabled:cursor-not-allowed',
    'hover:border-textMuted/40',
  ].join(' ');

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <Input
        label="Scenario Name *"
        id="tco-scenario-name"
        placeholder="e.g. Campus Wi-Fi Refresh 2026"
        value={values.scenario_name}
        onChange={handleChange('scenario_name')}
        disabled={calculating}
        error={fieldErrors.scenario_name}
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Input
          label="Device Count *"
          id="tco-device-count"
          type="number"
          placeholder="e.g. 48"
          value={values.device_count}
          onChange={handleChange('device_count')}
          disabled={calculating}
          error={fieldErrors.device_count}
        />

        <div className="flex flex-col gap-1">
          <label htmlFor="tco-device-category" className="text-xs font-medium text-textMuted">
            Device Category
          </label>
          <select
            id="tco-device-category"
            value={values.device_category}
            onChange={handleChange('device_category')}
            disabled={calculating}
            className={selectBase}
          >
            {DEVICE_CATEGORIES.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Input
          label="Hardware Cost / Unit (USD) *"
          id="tco-hardware-cost"
          type="number"
          placeholder="e.g. 1200"
          value={values.hardware_cost_per_unit}
          onChange={handleChange('hardware_cost_per_unit')}
          disabled={calculating}
          error={fieldErrors.hardware_cost_per_unit}
        />

        <Input
          label="Licensing Cost / Unit / Year (USD) *"
          id="tco-licensing-cost"
          type="number"
          placeholder="e.g. 180"
          value={values.licensing_cost_per_unit_year}
          onChange={handleChange('licensing_cost_per_unit_year')}
          disabled={calculating}
          error={fieldErrors.licensing_cost_per_unit_year}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Input
          label="Support Cost — Year 1 (USD)"
          id="tco-support-cost"
          type="number"
          placeholder="e.g. 5000 (optional, defaults to 0)"
          value={values.support_cost_year_one}
          onChange={handleChange('support_cost_year_one')}
          disabled={calculating}
          error={fieldErrors.support_cost_year_one}
        />

        <div className="flex flex-col gap-1">
          <label htmlFor="tco-lifecycle" className="text-xs font-medium text-textMuted">
            Lifecycle Years (1–5)
          </label>
          <select
            id="tco-lifecycle"
            value={values.lifecycle_years}
            onChange={handleChange('lifecycle_years')}
            disabled={calculating}
            className={selectBase}
          >
            {[1, 2, 3, 4, 5].map((yr) => (
              <option key={yr} value={String(yr)}>
                {yr} {yr === 1 ? 'year' : 'years'}
              </option>
            ))}
          </select>
          {fieldErrors.lifecycle_years && (
            <p className="text-xs text-red-400">{fieldErrors.lifecycle_years}</p>
          )}
        </div>
      </div>

      {/* PID amendment 1.3 — additional cost categories, hidden by default. */}
      <div className="border-t border-[var(--border)]/60 pt-3">
        <button
          type="button"
          onClick={() => setShowAdvanced((v) => !v)}
          className="flex items-center gap-1.5 text-xs font-medium text-textMuted hover:text-text transition-colors duration-150 focus:outline-none"
          aria-expanded={showAdvanced}
        >
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={`transition-transform duration-150 ${showAdvanced ? 'rotate-90' : ''}`}
            aria-hidden="true"
          >
            <polyline points="9 18 15 12 9 6" />
          </svg>
          {showAdvanced ? 'Hide' : 'Show'} additional costs (installation, accessories, spares, …)
        </button>

        {showAdvanced && (
          <div className="mt-3 flex flex-col gap-4">
            <p className="text-xs text-textMuted/80">
              All fields below are optional. Leaving a field blank explicitly
              means $0 for that cost — no silent defaults.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Installation / Professional Services (USD, Y1)"
                id="tco-installation"
                type="number"
                placeholder="e.g. 25000 (one-time)"
                value={values.installation_cost}
                onChange={handleChange('installation_cost')}
                disabled={calculating}
                error={fieldErrors.installation_cost}
              />

              <Input
                label="Accessories / Unit (USD, Y1)"
                id="tco-accessories"
                type="number"
                placeholder="e.g. 40 (mounts, cables, optics, PoE)"
                value={values.accessories_cost_per_unit}
                onChange={handleChange('accessories_cost_per_unit')}
                disabled={calculating}
                error={fieldErrors.accessories_cost_per_unit}
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Spares (% of device count, Y1)"
                id="tco-spares"
                type="number"
                placeholder="e.g. 10 = 10% extra units"
                value={values.spares_percent}
                onChange={handleChange('spares_percent')}
                disabled={calculating}
                error={fieldErrors.spares_percent}
              />

              <Input
                label="Migration / Training Labor (USD, Y1)"
                id="tco-training"
                type="number"
                placeholder="e.g. 4500 (one-time)"
                value={values.training_cost}
                onChange={handleChange('training_cost')}
                disabled={calculating}
                error={fieldErrors.training_cost}
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Recurring Support / Year (USD, Y2+)"
                id="tco-support-recurring"
                type="number"
                placeholder="e.g. 6000 (annual after Y1)"
                value={values.support_cost_recurring_per_year}
                onChange={handleChange('support_cost_recurring_per_year')}
                disabled={calculating}
                error={fieldErrors.support_cost_recurring_per_year}
              />

              <Input
                label="Adjacent Recurring / Year (USD, Y1–Y5)"
                id="tco-adjacent-recurring"
                type="number"
                placeholder="e.g. NAC renewal at 8000/year"
                value={values.adjacent_recurring_cost_per_year}
                onChange={handleChange('adjacent_recurring_cost_per_year')}
                disabled={calculating}
                error={fieldErrors.adjacent_recurring_cost_per_year}
              />
            </div>

            {/* PID amendment 1.5 — mid-cycle refresh events. */}
            <div className="pt-2">
              <p className="text-xs font-semibold text-textMuted mb-2">
                Mid-cycle hardware refreshes
              </p>
              <p className="text-xs text-textMuted/80 mb-3">
                Optional. Model phased refresh events inside the lifecycle
                (e.g. swap 25% of APs in Year 3). Refreshed units re-use
                existing licensing — only the hardware spend is added.
              </p>

              {refreshEvents.length === 0 && (
                <p className="text-xs text-textMuted/60 mb-2">
                  No refresh events. Click <span className="text-textMuted">Add refresh</span> to model one.
                </p>
              )}

              <div className="flex flex-col gap-3">
                {refreshEvents.map((row, i) => (
                  <div
                    key={i}
                    className="grid grid-cols-1 sm:grid-cols-[100px_140px_1fr_auto] gap-3 items-end"
                  >
                    <div className="flex flex-col gap-1">
                      <label
                        htmlFor={`refresh-year-${i}`}
                        className="text-xs font-medium text-textMuted"
                      >
                        Year (2–5)
                      </label>
                      <select
                        id={`refresh-year-${i}`}
                        value={row.year}
                        onChange={(e) => updateRefreshEvent(i, 'year', e.target.value)}
                        disabled={calculating}
                        className={selectBase}
                      >
                        {[2, 3, 4, 5].map((yr) => (
                          <option key={yr} value={String(yr)}>
                            {yr}
                          </option>
                        ))}
                      </select>
                      {refreshErrors[`${i}.year`] && (
                        <p className="text-xs text-red-400">{refreshErrors[`${i}.year`]}</p>
                      )}
                    </div>

                    <Input
                      label="% of fleet"
                      id={`refresh-percent-${i}`}
                      type="number"
                      placeholder="e.g. 25"
                      value={row.percent_of_devices}
                      onChange={(e) => updateRefreshEvent(i, 'percent_of_devices', e.target.value)}
                      disabled={calculating}
                      error={refreshErrors[`${i}.percent_of_devices`]}
                    />

                    <Input
                      label="Cost / unit override (USD, optional)"
                      id={`refresh-cost-${i}`}
                      type="number"
                      placeholder="Blank = use original hardware cost"
                      value={row.cost_per_unit_override}
                      onChange={(e) =>
                        updateRefreshEvent(i, 'cost_per_unit_override', e.target.value)
                      }
                      disabled={calculating}
                      error={refreshErrors[`${i}.cost_per_unit_override`]}
                    />

                    <button
                      type="button"
                      onClick={() => removeRefreshEvent(i)}
                      disabled={calculating}
                      className="self-end text-xs text-textMuted hover:text-red-400 transition-colors duration-150 px-2 py-2"
                      aria-label={`Remove refresh event ${i + 1}`}
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>

              <div className="mt-3">
                <button
                  type="button"
                  onClick={addRefreshEvent}
                  disabled={calculating}
                  className="text-xs font-medium text-accent hover:text-accent/80 transition-colors duration-150 focus:outline-none disabled:opacity-40"
                >
                  + Add refresh
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center justify-end pt-2">
        <Button variant="primary" type="submit" disabled={calculating}>
          {calculating ? 'Calculating…' : submitLabel || 'Calculate TCO'}
        </Button>
      </div>
    </form>
  );
}
