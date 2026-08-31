import {
  CardWrapper,
  CardNumber,
  CardTitle,
  CardDescription,
  CardLink,
} from './styles/FeatureCard.styles'

function FeatureCard({ number, title, description, linkText }) {
  return (
    <CardWrapper>
      <CardNumber>{number}</CardNumber>
      <CardTitle>{title}</CardTitle>
      <CardDescription>{description}</CardDescription>
      <CardLink>
        {linkText} →
      </CardLink>
    </CardWrapper>
  )
}

export default FeatureCard
