import { useState } from 'react'
import { CityMenu } from 'frontend'

const cities = [
  { slug: 'victoria', name: 'Victoria' },
  { slug: 'langford', name: 'Langford & West Shore' },
  { slug: 'nanaimo', name: 'Nanaimo' },
]

function Demo({ start }: { start: string | null }) {
  const [city, setCity] = useState(start)
  return (
    <div className="px-4 pb-48">
      <h1 className="display text-4xl leading-none tracking-tight">
        Massage openings{city && ` in ${cities.find((c) => c.slug === city)?.name}`}
      </h1>
      <CityMenu cities={cities} value={city} onChange={setCity} />
    </div>
  )
}

export const CitySelected = () => <Demo start="victoria" />
export const NoCityYet = () => <Demo start={null} />
