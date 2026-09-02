import {
  CardWrapper,
  CardNumber,
  CardTitle,
  CardDescription,
  CardLink,
} from './styles/FeatureCard.styles'

function FeatureCard({ number, title, description, linkText, onLinkClick }) {
  return (
    <CardWrapper onClick={onLinkClick} style={{ cursor: 'pointer' }}>
      <CardNumber>{number}</CardNumber>
      <CardTitle>{title}</CardTitle>
      <CardDescription>{description}</CardDescription>
      <CardLink onClick={onLinkClick}>
        {linkText} →
      </CardLink>
    </CardWrapper>
  )
}

export default FeatureCard
