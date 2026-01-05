import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { render } from '../../test/utils';
import { InfoCard } from './InfoCard';
import { CardContent } from '@mui/material';

describe('InfoCard', () => {
  it('renders children content', () => {
    render(
      <InfoCard>
        <CardContent>
          <div>Test Content</div>
        </CardContent>
      </InfoCard>
    );
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('renders default variant', () => {
    const { container } = render(
      <InfoCard variant="default">
        <CardContent>Default Card</CardContent>
      </InfoCard>
    );
    const card = container.querySelector('.MuiCard-root');
    expect(card).toBeInTheDocument();
  });

  it('renders highlighted variant', () => {
    const { container } = render(
      <InfoCard variant="highlighted">
        <CardContent>Highlighted Card</CardContent>
      </InfoCard>
    );
    const card = container.querySelector('.MuiCard-root');
    expect(card).toBeInTheDocument();
  });

  it('renders bordered variant', () => {
    const { container } = render(
      <InfoCard variant="bordered">
        <CardContent>Bordered Card</CardContent>
      </InfoCard>
    );
    const card = container.querySelector('.MuiCard-root');
    expect(card).toBeInTheDocument();
  });

  it('accepts custom sx prop', () => {
    const { container } = render(
      <InfoCard sx={{ minWidth: 500 }}>
        <CardContent>Custom Card</CardContent>
      </InfoCard>
    );
    expect(container.querySelector('.MuiCard-root')).toBeInTheDocument();
  });

  it('supports custom border color', () => {
    const { container } = render(
      <InfoCard sx={{ borderColor: 'red' }}>
        <CardContent>Custom Border</CardContent>
      </InfoCard>
    );
    expect(container.querySelector('.MuiCard-root')).toBeInTheDocument();
  });

  it('renders multiple children', () => {
    render(
      <InfoCard>
        <CardContent>
          <div>First Content</div>
        </CardContent>
        <CardContent>
          <div>Second Content</div>
        </CardContent>
      </InfoCard>
    );
    expect(screen.getByText('First Content')).toBeInTheDocument();
    expect(screen.getByText('Second Content')).toBeInTheDocument();
  });

  it('passes through additional Card props', () => {
    const { container } = render(
      <InfoCard data-testid="custom-card">
        <CardContent>Test</CardContent>
      </InfoCard>
    );
    expect(container.querySelector('[data-testid="custom-card"]')).toBeInTheDocument();
  });
});
