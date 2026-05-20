import { useState } from 'react';
import Card from '../ui/Card.jsx';
import Button from '../ui/Button.jsx';
import VendorFields from './VendorFields.jsx';
import CriteriaFields from './CriteriaFields.jsx';

const DEFAULT_VENDORS = ['', ''];
const DEFAULT_CRITERIA = ['Pricing', 'Support & SLA', 'Scalability'];

/**
 * ComparisonForm — collects vendors and criteria, then triggers generation.
 *
 * @param {function} onGenerate  — called with { vendors: string[], criteria: string[] } on valid submit
 * @param {boolean}  generating  — disables the form while the backend call is in-flight
 */
export default function ComparisonForm({ onGenerate, generating = false }) {
  const [vendors, setVendors] = useState(DEFAULT_VENDORS);
  const [criteria, setCriteria] = useState(DEFAULT_CRITERIA);
  const [vendorErrors, setVendorErrors] = useState({});
  const [criteriaErrors, setCriteriaErrors] = useState({});

  /* Clear individual vendor error on change */
  const handleVendorsChange = (updated) => {
    setVendors(updated);
    /* Clear errors for any index that is no longer empty */
    const cleared = { ...vendorErrors };
    updated.forEach((v, i) => {
      if (v.trim() && cleared[i]) {
        delete cleared[i];
      }
    });
    setVendorErrors(cleared);
  };

  /* Clear individual criterion error on change */
  const handleCriteriaChange = (updated) => {
    setCriteria(updated);
    const cleared = { ...criteriaErrors };
    updated.forEach((c, i) => {
      if (c.trim() && cleared[i]) {
        delete cleared[i];
      }
    });
    setCriteriaErrors(cleared);
  };

  /** Trim and collapse interior whitespace — mirrors backend normalization. */
  const normalize = (s) => s.replace(/\s+/g, ' ').trim();

  const validate = () => {
    const vErrors = {};
    const cErrors = {};

    const normalizedVendors = vendors.map(normalize);

    normalizedVendors.forEach((v, i) => {
      if (!v) {
        vErrors[i] = 'Vendor name is required.';
      }
    });

    const filledVendors = normalizedVendors.filter((v) => v);
    if (filledVendors.length < 2) {
      normalizedVendors.forEach((v, i) => {
        if (!v) vErrors[i] = 'Enter at least 2 vendor names.';
      });
    }

    // Duplicate / substring-containment guards mirror the backend
    // ComparisonRequest validator — catch paste errors before the request.
    const lowered = normalizedVendors.map((v) => v.toLowerCase());
    lowered.forEach((a, i) => {
      if (!a || vErrors[i]) return;
      lowered.forEach((b, j) => {
        if (i === j || !b) return;
        if (a === b) {
          vErrors[i] = 'Vendor names must be unique.';
        } else if (a.includes(b)) {
          vErrors[i] = `Looks like two names are merged here (contains "${normalizedVendors[j]}").`;
        }
      });
    });

    criteria.forEach((c, i) => {
      if (!normalize(c)) {
        cErrors[i] = 'Criterion cannot be empty.';
      }
    });

    const filledCriteria = criteria.filter((c) => normalize(c));
    if (filledCriteria.length < 1) {
      criteria.forEach((c, i) => {
        if (!normalize(c)) cErrors[i] = 'Enter at least one criterion.';
      });
    }

    return { vErrors, cErrors, normalizedVendors };
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    const { vErrors, cErrors, normalizedVendors } = validate();

    if (Object.keys(vErrors).length > 0 || Object.keys(cErrors).length > 0) {
      setVendorErrors(vErrors);
      setCriteriaErrors(cErrors);
      return;
    }

    onGenerate({
      vendors: normalizedVendors,
      criteria: criteria.map(normalize),
    });
  };

  return (
    <Card title="Comparison Setup">
      <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-6">
        <VendorFields
          vendors={vendors}
          onChange={handleVendorsChange}
          errors={vendorErrors}
          disabled={generating}
        />

        <CriteriaFields
          criteria={criteria}
          onChange={handleCriteriaChange}
          errors={criteriaErrors}
          disabled={generating}
        />

        {/* In-progress message */}
        {generating && (
          <div className="flex items-start gap-3 rounded-lg border border-accent/20 bg-accent/8 px-4 py-3">
            <svg
              className="mt-0.5 shrink-0 animate-spin text-accent"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M21 12a9 9 0 1 1-6.219-8.56" />
            </svg>
            <div>
              <p className="text-sm font-medium text-accent">Researching vendors and building the matrix…</p>
              <p className="text-xs text-textMuted mt-0.5">
                This can take up to a minute — we&apos;re running live research per vendor plus AI synthesis.
              </p>
            </div>
          </div>
        )}

        <div className="flex items-center justify-end pt-1">
          <Button variant="primary" type="submit" disabled={generating}>
            {generating ? 'Generating…' : 'Generate comparison'}
          </Button>
        </div>
      </form>
    </Card>
  );
}
