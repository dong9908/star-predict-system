import styled from 'styled-components'

const FooterWrapper = styled.footer`
  border-top: 1px solid rgba(30, 41, 59, 0.8);
  background: rgba(15, 23, 42, 0.5);
  padding: 2rem 1.5rem;
  margin-top: auto;
`

const FooterContent = styled.div`
  max-width: 80rem;
  margin: 0 auto;
  text-align: center;
  color: #94a3b8;
  font-size: 0.875rem;
`

function Footer() {
  return (
    <FooterWrapper>
      <FooterContent>
        <p>© 2024 ASTRA. All rights reserved.</p>
      </FooterContent>
    </FooterWrapper>
  )
}

export default Footer
