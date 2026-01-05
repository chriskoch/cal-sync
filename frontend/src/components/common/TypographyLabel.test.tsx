import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { render } from '../../test/utils';
import { TypographyLabel } from './TypographyLabel';

describe('TypographyLabel', () => {
  it('renders children text', () => {
    render(<TypographyLabel>Test Text</TypographyLabel>);
    expect(screen.getByText('Test Text')).toBeInTheDocument();
  });

  it('renders heading variant', () => {
    render(<TypographyLabel variant="heading">Heading Text</TypographyLabel>);
    expect(screen.getByText('Heading Text')).toBeInTheDocument();
  });

  it('renders subheading variant', () => {
    render(<TypographyLabel variant="subheading">Subheading Text</TypographyLabel>);
    expect(screen.getByText('Subheading Text')).toBeInTheDocument();
  });

  it('renders label variant (default)', () => {
    render(<TypographyLabel variant="label">Label Text</TypographyLabel>);
    expect(screen.getByText('Label Text')).toBeInTheDocument();
  });

  it('renders caption variant', () => {
    render(<TypographyLabel variant="caption">Caption Text</TypographyLabel>);
    expect(screen.getByText('Caption Text')).toBeInTheDocument();
  });

  it('accepts custom sx prop', () => {
    const { container } = render(
      <TypographyLabel sx={{ color: 'red' }}>Custom Style</TypographyLabel>
    );
    expect(container.querySelector('.MuiTypography-root')).toBeInTheDocument();
  });

  it('supports component prop', () => {
    render(
      <TypographyLabel component="h1">
        Heading as H1
      </TypographyLabel>
    );
    const heading = screen.getByText('Heading as H1');
    expect(heading.tagName).toBe('H1');
  });

  it('renders multiple children', () => {
    render(
      <TypographyLabel>
        First text <strong>bold text</strong> last text
      </TypographyLabel>
    );
    expect(screen.getByText(/First text/)).toBeInTheDocument();
    expect(screen.getByText('bold text')).toBeInTheDocument();
  });

  it('passes through additional Typography props', () => {
    render(
      <TypographyLabel align="center" data-testid="centered-text">
        Centered
      </TypographyLabel>
    );
    expect(screen.getByTestId('centered-text')).toBeInTheDocument();
  });

  it('supports nested elements', () => {
    render(
      <TypographyLabel>
        Text with <span data-testid="nested-span">nested span</span>
      </TypographyLabel>
    );
    expect(screen.getByTestId('nested-span')).toBeInTheDocument();
  });
});
